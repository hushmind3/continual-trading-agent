"""Serialize writers and tolerate short Windows file-sharing conflicts."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
import threading
import time
from weakref import WeakValueDictionary

_locks = WeakValueDictionary()
_guard = threading.Lock()


def read_json(path: str | Path, fallback=None):
    """Read persisted state; each failure returns a caller-owned default."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return deepcopy(fallback) if fallback is not None else {}


def atomic_json(value, path: str | Path, default=None) -> None:
    path = Path(path)
    with _guard:
        key = str(path.resolve())
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        try:
            temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=default), encoding="utf-8")
            for attempt in range(8):
                try:
                    os.replace(temporary, path)
                    break
                except PermissionError:
                    if attempt == 7:
                        raise
                    time.sleep(0.025 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)

from contextlib import closing
import hashlib
import shutil
import sqlite3
import zlib

# Deduplicated MoE evidence and bounded runtime diagnostics.
LOG_BYTES = 4 * 1024 * 1024
CACHE_ROWS = 64


def evidence_status(state):
    """Read cache counters without creating storage or decoding native outputs."""
    path = Path(state) / "evidence.sqlite3"
    if not path.is_file():
        return {"available": False}
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            counts = {name: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                      for name, table in (("stored_outputs", "packets"), ("stored_decisions", "contexts"), ("cycles", "cache"))}
            counts["market_outputs"] = db.execute("SELECT COUNT(*) FROM refs WHERE owner='market'").fetchone()[0]
            counts["latest_as_of"] = db.execute("SELECT MAX(stamp) FROM cache").fetchone()[0]
        size = 0
        for file in (path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")):
            try:
                size += file.stat().st_size
            except FileNotFoundError:
                pass
        return {"available": True, "bytes": size, **counts}
    except (OSError, sqlite3.Error) as exc:
        return {"available": False, "error": type(exc).__name__}


def retire_trial_debug(directory, trash):
    directory = Path(directory).resolve()
    trash = Path(trash).resolve()
    for name in ("decisions.jsonl", "progress.json"):
        for path in directory.rglob(name):
            target = trash / path.relative_to(directory)
            target.parent.mkdir(parents=True, exist_ok=True)
            number = 0
            while target.exists():
                number += 1
                target = target.with_name(path.name + f".{number}")
            shutil.move(str(path), str(target))


def append_log(path, row, max_bytes=LOG_BYTES):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if path.exists() and path.stat().st_size + len(data) > max_bytes:
        path.replace(path.with_name(path.name + ".1"))
    with path.open("ab") as stream:
        stream.write(data)


def rotate_worker_log(path):
    """Only called before a worker opens its output handle."""
    path = Path(path)
    if path.exists() and path.stat().st_size >= LOG_BYTES:
        path.replace(path.with_name(path.name + ".1"))


class WorkerLog:
    """Close each write so Windows can rotate output while the worker runs."""
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def write(self, text):
        data = text.encode("utf-8", errors="replace")
        with self.lock:
            size = min(65536, LOG_BYTES)
            for offset in range(0, len(data), size):
                chunk = data[offset:offset + size]
                if self.path.exists() and self.path.stat().st_size + len(chunk) > LOG_BYTES:
                    self.path.replace(self.path.with_name(self.path.name + ".1"))
                with self.path.open("ab") as stream:
                    stream.write(chunk)
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return False


def _encode(value):
    return zlib.compress(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(), 3)


def _decode(value):
    return json.loads(zlib.decompress(value))


class EvidenceJournal:
    def __init__(self, state):
        self.path = Path(state) / "evidence.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS packets (id TEXT PRIMARY KEY, data BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS contexts (stamp TEXT PRIMARY KEY, data BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS cache (stamp TEXT PRIMARY KEY, data BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS refs (owner TEXT, id TEXT, PRIMARY KEY(owner,id));
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, data BLOB NOT NULL);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA auto_vacuum=INCREMENTAL")
        return db

    def _packet_ids(self, db, packets):
        ids = []
        for packet in packets:
            data = _encode(packet)
            key = hashlib.sha256(data).hexdigest()
            db.execute("INSERT OR IGNORE INTO packets VALUES (?,?)", (key, data))
            ids.append(key)
        return ids

    def _references(self, db, owner, ids):
        db.execute("DELETE FROM refs WHERE owner=?", (owner,))
        db.executemany("INSERT OR IGNORE INTO refs VALUES (?,?)", ((owner, key) for key in ids))

    def _decision(self, db, decision):
        if not decision:
            return None
        keys = ("as_of", "currencies", "trading_output", "tradable_symbols", "used_experts",
                "selected_experts", "evidence_as_of", "policy_validity", "decision_seconds",
                "native_decision_seconds", "current_weights")
        result = {key: decision[key] for key in keys if key in decision}
        result["evidence_refs"] = self._packet_ids(db, decision["raw_outputs"])
        return result

    def _restore_decision(self, db, decision):
        if decision is None:
            return None
        decision = dict(decision)
        packets = []
        for key in decision.pop("evidence_refs"):
            row = db.execute("SELECT data FROM packets WHERE id=?", (key,)).fetchone()
            if row is None:
                raise ValueError("Missing saved expert evidence: " + key)
            packets.append(_decode(row[0]))
        decision["raw_outputs"] = packets
        return decision

    def save_contexts(self, contexts, checkpoint_saved=False):
        with closing(self._connect()) as db, db:
            for stamp, (snapshot, decision) in contexts.items():
                packed = self._decision(db, decision)
                # Training consumes symbol/account state, not expert input arrays.
                snapshot = {key: value for key, value in snapshot.items() if key not in ("expert_inputs","stock_policy_history")}
                data = _encode({"snapshot": snapshot, "decision": packed})
                previous = db.execute("SELECT data FROM contexts WHERE stamp=?", (stamp,)).fetchone()
                if previous is None or previous[0] != data:
                    db.execute("INSERT OR REPLACE INTO contexts VALUES (?,?)", (stamp, data))
                    self._references(db, "context:" + stamp, packed["evidence_refs"])
            if checkpoint_saved:
                for (stamp,) in db.execute("SELECT stamp FROM contexts").fetchall():
                    if stamp not in contexts:
                        db.execute("DELETE FROM contexts WHERE stamp=?", (stamp,))
                        db.execute("DELETE FROM refs WHERE owner=?", ("context:" + stamp,))
                self._collect(db)

    def migrate_legacy_contexts(self):
        path = self.path.parent / "pending_contexts.json"
        if path.is_file():
            contexts = {stamp: (context["snapshot"], {
                "trading_output": context["trading_output"], "raw_outputs": context["raw_outputs"]})
                for stamp, context in json.loads(path.read_text(encoding="utf-8")).items()}
            self.save_contexts(contexts)

    def load_contexts(self):
        result = {}
        with closing(self._connect()) as db:
            for stamp, data in db.execute("SELECT stamp,data FROM contexts"):
                record = _decode(data)
                result[stamp] = (record["snapshot"], self._restore_decision(db, record["decision"]))
        return result

    def save_market(self, packets):
        with closing(self._connect()) as db, db:
            ids = self._packet_ids(db, packets)
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('market',?)", (_encode(ids),))
            self._references(db, "market", ids)

    def record_cycle(self, row):
        with closing(self._connect()) as db, db:
            decision = self._decision(db, row.get("decision"))
            books = {currency: {key: book.get(key) for key in
                     ("equity", "cash", "net_pnl", "trade_count", "fees", "slippage")}
                     for currency, book in row.get("books", {}).items()}
            summary = {key: row.get(key) for key in ("timestamp", "seconds", "reward_points", "replay_rows")}
            summary.update(decision=decision, books=books, fills=row.get("fills", []),
                           order_ids=(row.get("orders") or {}).get("orders", []))
            stamp = row["timestamp"]
            db.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (stamp, _encode(summary)))
            self._references(db, "cache:" + stamp, decision["evidence_refs"] if decision else [])
            stale = db.execute("SELECT stamp FROM cache ORDER BY stamp DESC LIMIT -1 OFFSET ?", (CACHE_ROWS,)).fetchall()
            for (old,) in stale:
                db.execute("DELETE FROM cache WHERE stamp=?", (old,))
                db.execute("DELETE FROM refs WHERE owner=?", ("cache:" + old,))
            self._collect(db)
        append_log(self.path.parent / "cycles.jsonl", summary)
        return summary

    def cached_rows(self):
        with closing(self._connect()) as db:
            rows = [_decode(data) for (data,) in db.execute("SELECT data FROM cache ORDER BY stamp")]
            for row in rows:
                row["decision"] = self._restore_decision(db, row["decision"])
            return rows

    @staticmethod
    def _collect(db):
        db.execute("DELETE FROM packets WHERE id NOT IN (SELECT id FROM refs)")
        db.execute("PRAGMA incremental_vacuum(64)")
