"""Bounded, deduplicated storage for normalized market bars."""
from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .paths import ensure_project_path

FEED_COLUMNS = [
    "date", "symbol", "market", "asset_class", "open", "high", "low", "close", "volume",
    "bid", "ask", "bid_size", "ask_size", "buy_volume", "sell_volume", "trade_count",
    "implied_volatility", "open_interest", "yield_change", "days_to_expiry",
]


class AppendOnlyMarketCSV:
    """Append bars once; compact only history acknowledged by the observer."""
    RETAIN_TIMESTAMPS = 512
    REFERENCE_CARRY_ROWS = 128
    DEDUPE_DAYS = 8
    COMPACT_CSV_BYTES = 16 * 1024 * 1024
    COMPACT_INDEX_BYTES = 16 * 1024 * 1024

    def __init__(self, path: str | Path):
        self.path = ensure_project_path(path, "market data")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = self.path.with_suffix(self.path.suffix + ".sqlite3")
        self.db = sqlite3.connect(self.db_path, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS seen (symbol TEXT NOT NULL, stamp_ns INTEGER NOT NULL, PRIMARY KEY(symbol,stamp_ns))")
        self.db.execute("CREATE INDEX IF NOT EXISTS seen_stamp_idx ON seen(stamp_ns)")
        self.db.commit()
        self._next_csv_compaction = self.COMPACT_CSV_BYTES
        self._next_index_compaction = self.COMPACT_INDEX_BYTES
        self._seed_index()

    def _seed_index(self) -> None:
        # Recover keys if a prior process stopped after writing CSV but before
        # committing the corresponding SQLite transaction.
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        for chunk in pd.read_csv(self.path, usecols=["date", "symbol"], chunksize=100_000):
            stamps = pd.to_datetime(chunk["date"], utc=True, errors="coerce")
            rows = [(str(symbol), int(stamp.value)) for symbol, stamp in zip(chunk.symbol, stamps) if not pd.isna(stamp)]
            with self.db:
                self.db.executemany("INSERT OR IGNORE INTO seen VALUES (?,?)", rows)

    def append(self, rows: list[dict[str, Any]]) -> int:
        unique: list[dict[str, Any]] = []
        batch: set[tuple[str, int]] = set()
        if not rows:return 0
        stamps=pd.to_datetime([r.get('date') for r in rows],utc=True,errors='coerce',format='mixed')
        valid=[s.value for s in stamps if not pd.isna(s)]
        if not valid:return 0
        symbols=sorted({str(r.get('symbol')) for r in rows if r.get('symbol')})
        existing=set()
        for start in range(0,len(symbols),400):
            group=symbols[start:start+400]
            placeholders=','.join('?' for _ in group)
            existing.update(self.db.execute(f'SELECT symbol,stamp_ns FROM seen WHERE stamp_ns BETWEEN ? AND ? AND symbol IN ({placeholders})',
                                            (min(valid),max(valid),*group)).fetchall())
        for row,stamp in zip(rows,stamps):
            row = {key: row.get(key) for key in FEED_COLUMNS}
            if pd.isna(stamp) or not row["symbol"]:
                continue
            row["date"] = stamp.isoformat()
            key = (str(row["symbol"]), int(stamp.value))
            if key in batch or key in existing:
                continue
            batch.add(key)
            unique.append(row)
        if not unique:
            return 0
        fresh = not self.path.exists() or self.path.stat().st_size == 0
        with self.path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FEED_COLUMNS, extrasaction="ignore")
            if fresh:
                writer.writeheader()
            writer.writerows(unique)
            f.flush()
            os.fsync(f.fileno())
        with self.db:
            self.db.executemany("INSERT OR IGNORE INTO seen VALUES (?,?)",
                                [(str(r["symbol"]), int(pd.Timestamp(r["date"]).value)) for r in unique])
        self._compact_if_needed()
        return len(unique)

    def _compact_if_needed(self) -> None:
        wal = self.db_path.with_name(self.db_path.name + "-wal")
        csv_bytes = self.path.stat().st_size if self.path.exists() else 0
        index_bytes = sum(p.stat().st_size for p in (self.db_path, wal) if p.exists())
        if csv_bytes < self._next_csv_compaction and index_bytes < self._next_index_compaction:
            return
        if not self.path.exists() or csv_bytes == 0:
            return
        temporary = self.path.with_suffix(self.path.suffix + ".compact.tmp")
        recent_temporary = self.path.with_suffix(self.path.suffix + ".recent.tmp")
        try:
            latest_rows = self.db.execute(
                "SELECT DISTINCT stamp_ns FROM seen ORDER BY stamp_ns DESC LIMIT ?",
                (self.RETAIN_TIMESTAMPS,)).fetchall()
            if not latest_rows:
                return
            cutoff_ns = int(latest_rows[-1][0]) if len(latest_rows) >= self.RETAIN_TIMESTAMPS else None
            latest_ns = int(latest_rows[0][0])
            cursor_path = self.path.parent / "agent" / "live_cursor.json"
            try:
                cursor = json.loads(cursor_path.read_text(encoding="utf-8")).get("last_timestamp")
                cursor_ns = int(pd.to_datetime(cursor, utc=True).value) if cursor else None
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                cursor_ns = None
            if cursor_ns is None:
                return
            context_rows = self.db.execute(
                "SELECT DISTINCT stamp_ns FROM seen WHERE stamp_ns<=? ORDER BY stamp_ns DESC LIMIT 128",
                (cursor_ns,)).fetchall()
            if not context_rows:
                return
            protected_ns = int(context_rows[-1][0])
            cutoff_ns = min(cutoff_ns, protected_ns) if cutoff_ns is not None else None
            carry_by_symbol = {}
            recent_counts = {}
            wrote_recent = False
            for chunk in pd.read_csv(self.path, chunksize=100_000):
                stamps = pd.to_datetime(chunk["date"], utc=True, errors="coerce")
                if cutoff_ns is None:
                    recent_mask = stamps.notna()
                else:
                    stamp_ns = stamps.astype("int64", copy=False)
                    recent_mask = stamps.notna() & (stamp_ns >= cutoff_ns)
                    old_reference = chunk.loc[stamps.notna() & (stamp_ns < cutoff_ns)]
                    for symbol, rows in old_reference.groupby("symbol", sort=False):
                        prior = carry_by_symbol.get(symbol)
                        merged = rows if prior is None else pd.concat((prior, rows), ignore_index=True)
                        carry_by_symbol[symbol] = merged.sort_values("date", kind="stable").tail(self.REFERENCE_CARRY_ROWS)
                recent = chunk.loc[recent_mask]
                if not recent.empty:
                    for symbol, count in recent.groupby("symbol").size().items():
                        recent_counts[symbol] = recent_counts.get(symbol, 0) + int(count)
                    recent.to_csv(recent_temporary, index=False, columns=FEED_COLUMNS,
                                  mode="a" if wrote_recent else "w", header=not wrote_recent)
                    wrote_recent = True
            carry_rows = [rows.tail(max(0, self.REFERENCE_CARRY_ROWS - recent_counts.get(symbol, 0)))
                          for symbol, rows in carry_by_symbol.items()]
            carry = (pd.concat(carry_rows, ignore_index=True)
                     if carry_rows else pd.DataFrame(columns=FEED_COLUMNS))
            if not carry.empty:
                carry = carry.sort_values(["date", "symbol"], kind="stable")
            carry.to_csv(temporary, index=False, columns=FEED_COLUMNS)
            if wrote_recent:
                with recent_temporary.open("rb") as source, temporary.open("ab") as target:
                    source.readline()
                    shutil.copyfileobj(source, target, 1024 * 1024)
            with temporary.open("rb+") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            keep_after = latest_ns - int(pd.Timedelta(days=self.DEDUPE_DAYS).value)
            with self.db:
                self.db.execute("DELETE FROM seen WHERE stamp_ns < ?", (keep_after,))
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.execute("VACUUM")
        except (OSError, sqlite3.Error, pd.errors.ParserError, ValueError) as exc:
            logging.getLogger(__name__).warning("Could not compact live market cache: %s", exc)
        finally:
            temporary.unlink(missing_ok=True)
            recent_temporary.unlink(missing_ok=True)
        if self.path.exists():
            self._next_csv_compaction = self.COMPACT_CSV_BYTES
            self._next_index_compaction = self.COMPACT_INDEX_BYTES

    def close(self):
        self.db.close()
