"""Bounded, durable portfolio transitions; recovery never replays an applied update."""
from __future__ import annotations

import io
import hashlib
import json
import sqlite3
import threading
import time
import zlib
from contextlib import contextmanager
from pathlib import Path


def encode(value):
    import torch
    def plain(item):
        if not isinstance(item,dict) and hasattr(item,"to_dict"):
            item=item.to_dict()
        if isinstance(item,dict): return {k:plain(v) for k,v in item.items()}
        if isinstance(item,(tuple,list)): return [plain(v) for v in item]
        return item
    stream = io.BytesIO()
    torch.save(plain(value), stream)
    return zlib.compress(stream.getvalue(), 3)


def decode(value):
    import torch
    return torch.load(io.BytesIO(zlib.decompress(value)), map_location="cpu", weights_only=True)


class Journal:
    def __init__(self, path: Path, limit_mib=512, retention=10000):
        self.path, self.retention = Path(path), int(retention)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.depth = 0
        self.db = sqlite3.connect(path, timeout=10, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA journal_size_limit=4194304")
        self.db.execute(f"PRAGMA max_page_count={int(limit_mib)*256}")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS transitions(id INTEGER PRIMARY KEY, topology TEXT NOT NULL,
          version INTEGER NOT NULL, created REAL NOT NULL, payload BLOB NOT NULL, learned INTEGER);
        CREATE INDEX IF NOT EXISTS transitions_ready ON transitions(learned, version, topology);
        CREATE TABLE IF NOT EXISTS pending(currency TEXT PRIMARY KEY, payload BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS evidence(expert TEXT PRIMARY KEY, payload BLOB NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, payload BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS nav(currency TEXT NOT NULL, stamp TEXT NOT NULL, equity REAL NOT NULL,
          cash REAL NOT NULL, costs REAL NOT NULL, PRIMARY KEY(currency,stamp));
        CREATE TABLE IF NOT EXISTS allocations(currency TEXT NOT NULL, stamp TEXT NOT NULL,
          weights TEXT NOT NULL, PRIMARY KEY(currency,stamp));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, created REAL NOT NULL,
          kind TEXT NOT NULL, detail TEXT NOT NULL, read INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS fills(identity TEXT PRIMARY KEY,currency TEXT NOT NULL,sequence INTEGER NOT NULL,
          stamp TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS fills_currency_sequence ON fills(currency,sequence DESC);
        """)
        self.db.commit()

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            self.depth += 1
            try:
                yield
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise
            finally:
                self.depth -= 1

    def commit(self):
        if not self.depth:
            self.db.commit()

    def get_state(self, key):
        with self.lock:
            row = self.db.execute("SELECT payload FROM state WHERE key=?", (key,)).fetchone()
            return json.loads(zlib.decompress(row[0])) if row else None

    def set_state(self, key, value):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO state VALUES(?,?)", (key,zlib.compress(json.dumps(value).encode(),3)))
            self.commit()

    def record_nav(self, currency, stamp, book):
        with self.lock:
            costs=sum(book.get(k,0) for k in ("fees","slippage","spread","sell_tax"))
            self.db.execute("INSERT OR REPLACE INTO nav VALUES(?,?,?,?,?)", (currency,stamp,book["equity"],book["cash"],costs))
            self.db.execute("DELETE FROM nav WHERE stamp < COALESCE((SELECT stamp FROM nav ORDER BY stamp DESC LIMIT 1 OFFSET 5000),'')")
            self.commit()

    def record_weights(self, currency, stamp, weights):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO allocations VALUES(?,?,?)", (currency,stamp,json.dumps(weights)))
            self.db.execute("DELETE FROM allocations WHERE stamp < COALESCE((SELECT stamp FROM allocations ORDER BY stamp DESC LIMIT 1 OFFSET 5000),'')")
            self.commit()

    def record_fills(self, fills, books):
        """Persist actual executions before the bounded account preview can evict them."""
        with self.lock:
            for currency,book in books.items():
                items=[f for f in fills if f['currency']==currency]
                start=int(book.get('trade_count',0))-len(items)
                for index,fill in enumerate(items,1):
                    sequence=int(fill.get('sequence',start+index))
                    key=[currency,sequence,fill.get('date'),fill['symbol'],fill['action'],fill.get('decision_id'),fill['quantity'],fill['price']]
                    identity=hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest()
                    self.db.execute('INSERT OR IGNORE INTO fills VALUES(?,?,?,?,?)',
                        (identity,currency,sequence,str(fill.get('date','')),json.dumps({**fill,'sequence':sequence})))
            self.commit()

    def fill_count(self,currency):
        with self.lock:return self.db.execute('SELECT COUNT(*) FROM fills WHERE currency=?',(currency,)).fetchone()[0]

    def fills(self,currency,offset=0,limit=50,before=None):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute(
                'SELECT payload FROM fills WHERE currency=? AND (? IS NULL OR sequence<?) ORDER BY sequence DESC,stamp DESC LIMIT ? OFFSET ?',
                (currency,before,before,limit,offset))]

    def history(self, currency, limit=300):
        with self.lock:
            return [dict(as_of=t,equity=e,cash=c,costs=f) for t,e,c,f in reversed(self.db.execute(
                "SELECT stamp,equity,cash,costs FROM nav WHERE currency=? ORDER BY stamp DESC LIMIT ?",(currency,limit)).fetchall())]

    def weights(self, currency):
        with self.lock:
            return [(stamp,json.loads(weights)) for stamp,weights in self.db.execute(
                "SELECT stamp,weights FROM allocations WHERE currency=? ORDER BY stamp",(currency,))]

    def pending(self):
        with self.lock:
            return {currency: decode(payload) for currency, payload in self.db.execute("SELECT currency,payload FROM pending")}

    def replace_pending(self, currency, payload):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO pending VALUES(?,?)", (currency, encode(payload)))
            self.commit()

    def settle(self, currency, topology, version, payload):
        with self.lock:
            self.db.execute("INSERT INTO transitions(topology,version,created,payload) VALUES(?,?,?,?)",
                            (topology, version, time.time(), encode(payload)))
            self.db.execute("DELETE FROM pending WHERE currency=?", (currency,))
            self.db.execute("DELETE FROM transitions WHERE learned IS NOT NULL AND id < "
                            "COALESCE((SELECT id FROM transitions ORDER BY id DESC LIMIT 1 OFFSET ?),0)", (self.retention,))
            self.commit()

    def batch(self, version, lag, size):
        with self.lock:
            self.db.execute("UPDATE transitions SET learned=-1 WHERE learned IS NULL AND version<?",(max(0,version-lag),))
            self.db.execute("DELETE FROM transitions WHERE learned IS NOT NULL AND id < COALESCE("
                            "(SELECT id FROM transitions ORDER BY id DESC LIMIT 1 OFFSET ?),0)",(self.retention,))
            self.commit()
            group = self.db.execute("SELECT topology FROM transitions WHERE learned IS NULL AND version BETWEEN ? AND ? "
                "GROUP BY topology HAVING COUNT(*)>=? ORDER BY MIN(id) LIMIT 1", (max(0, version-lag), version, size)).fetchone()
            if not group:
                return [], []
            rows = self.db.execute("SELECT id,payload FROM transitions WHERE topology=? AND learned IS NULL "
                "AND version BETWEEN ? AND ? ORDER BY id LIMIT ?", (group[0], max(0, version-lag), version, size)).fetchall()
            return [r[0] for r in rows], [decode(r[1]) for r in rows]

    def evidence(self):
        with self.lock:
            return {key: json.loads(zlib.decompress(value)) for key,value in self.db.execute("SELECT expert,payload FROM evidence")}

    def put_evidence(self, expert, value):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO evidence VALUES(?,?,?)", (expert,zlib.compress(json.dumps(value).encode(),3),time.time()))
            self.commit()

    def acknowledge(self, ids, version):
        with self.lock:
            self.db.executemany("UPDATE transitions SET learned=? WHERE id=? AND learned IS NULL", [(version, int(i)) for i in ids])
            self.commit()

    def event(self, kind, detail):
        with self.lock:
            self.db.execute("INSERT INTO events(created,kind,detail) VALUES(?,?,?)", (time.time(), kind, str(detail)))
            self.db.execute("DELETE FROM events WHERE id < COALESCE((SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET 200),0)")
            self.commit()

    def events(self):
        with self.lock:
            return [dict(id=i, time=t, kind=k, detail=d, read=bool(r)) for i,t,k,d,r in
                    self.db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100")]

    def read_events(self, through=None):
        with self.lock:
            if through is None:
                self.db.execute("UPDATE events SET read=1 WHERE read=0")
            else:
                self.db.execute("UPDATE events SET read=1 WHERE read=0 AND id<=?",(int(through),))
            self.commit()

    def stats(self, version=0, lag=2):
        with self.lock:
            total, completed, outdated = self.db.execute("SELECT COUNT(*),SUM(learned>=0),"
                "SUM(learned=-1 OR (learned IS NULL AND version<?)) FROM transitions", (max(0, version-lag),)).fetchone()
            pending = self.db.execute("SELECT COUNT(*) FROM pending").fetchone()[0]
            groups=[]
            for topology,count in self.db.execute(
                'SELECT topology,COUNT(*) FROM transitions WHERE learned IS NULL AND version BETWEEN ? AND ? GROUP BY topology',
                (max(0,version-lag),version)):
                try:assets=len(json.loads(topology))
                except (ValueError,TypeError):assets=None
                groups.append(dict(assets=assets,ready=count))
        size = sum(p.stat().st_size for p in [self.path, Path(str(self.path)+'-wal')] if p.exists())
        return dict(total=total, completed=completed or 0, outdated=outdated or 0, pending=pending,
                    ready=total-(completed or 0)-(outdated or 0),batch_ready=max((g['ready'] for g in groups),default=0),
                    groups=groups,bytes=size)

    def close(self):
        self.db.close()
