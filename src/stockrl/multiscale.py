"""Official FinRL-X daily store adapter and frozen Expert history reader."""
from __future__ import annotations

from collections import defaultdict
from contextlib import closing
import math
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

from .paths import ensure_project_path
from .state_io import read_json
from .paths import PROJECT_ROOT


_RULES=read_json(PROJECT_ROOT/'configs/market_context.json')
DAILY_ENCODER_BARS=int(_RULES.get('daily_encoder_bars',1300))
_DAILY_ROWS_CACHE=None

class DailyBarStore:
    """Bounded multi-year completed daily OHLCV rows per symbol."""

    MAX_BARS_PER_SYMBOL = int(_RULES.get("daily_store_bars_per_symbol",1500))

    def __init__(self, path: str | Path):
        self.path = ensure_project_path(path, "multiscale daily bars")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        from .platform.finrl_modules import DataStore
        self.store=DataStore.__new__(DataStore)
        self.store.base_dir=self.path.parent;self.store.processed_dir=self.path.parent/'processed';self.store.db_path=self.path
        self.store._init_database()
        self.db=sqlite3.connect(self.path,timeout=30);self.db.execute('PRAGMA journal_mode=WAL')
        kind=self.db.execute("SELECT type FROM sqlite_master WHERE name='daily_bars'").fetchone()
        if kind and kind[0]=='table':
            for frame in pd.read_sql_query('SELECT * FROM daily_bars',self.db,chunksize=5000):
                frame['date']=pd.to_datetime(frame.stamp_ns,utc=True).map(lambda v:v.isoformat())
                self.store.save_price_data(frame.rename(columns={'symbol':'ticker'}))
            self.db.execute('DROP TABLE daily_bars')
        self.db.execute("CREATE VIEW IF NOT EXISTS daily_bars AS SELECT ticker AS symbol,CAST(strftime('%s',date) AS INTEGER)*1000000000 AS stamp_ns,open,high,low,close,volume FROM price_data")
        self.db.commit()

    def has_symbol(self, symbol: str) -> bool:
        return self.db.execute(
            "SELECT 1 FROM daily_bars WHERE symbol=? LIMIT 1", (symbol,)).fetchone() is not None

    def needs_long_history(self,symbol):
        count=self.db.execute("SELECT COUNT(*) FROM daily_bars WHERE symbol=?",(symbol,)).fetchone()[0]
        return count<DAILY_ENCODER_BARS

    def symbol_count(self) -> int:
        return int(self.db.execute("SELECT COUNT(DISTINCT symbol) FROM daily_bars").fetchone()[0])

    def upsert(self, rows: list[dict]) -> int:
        values = []
        for row in rows:
            try:
                stamp = int(pd.Timestamp(row["date"]).value)
                bar = tuple(float(row[key]) for key in ("open", "high", "low", "close", "volume"))
                if not row.get("symbol") or not all(math.isfinite(x) for x in bar) or bar[3] <= 0:
                    continue
                values.append((str(row["symbol"]), stamp, *bar))
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        if not values:
            return 0
        frame=pd.DataFrame(values,columns=['ticker','stamp_ns','open','high','low','close','volume'])
        frame['date']=pd.to_datetime(frame.stamp_ns,utc=True).map(lambda v:v.isoformat());frame['adj_close']=frame.close
        count=self.store.save_price_data(frame)
        with self.db:
            for symbol in frame.ticker.unique():
                cutoff=self.db.execute('SELECT date FROM price_data WHERE ticker=? ORDER BY date DESC LIMIT 1 OFFSET ?',(symbol,self.MAX_BARS_PER_SYMBOL-1)).fetchone()
                if cutoff:self.db.execute('DELETE FROM price_data WHERE ticker=? AND date<?',(symbol,cutoff[0]))
        return count

    def close(self) -> None:
        self.db.close()
        import gc
        gc.collect()


def _load_daily(path: Path, symbols: set[str], latest_ns: int) -> dict[str, list[tuple]]:
    global _DAILY_ROWS_CACHE
    if not path.is_file() or not symbols:
        return {}
    uri = f"{path.resolve().as_uri()}?mode=ro"
    try:
        signature=(str(path.resolve()),tuple((p.stat().st_size,p.stat().st_mtime_ns)
            if p.exists() else None for p in (path,Path(str(path)+"-wal"))))
        if _DAILY_ROWS_CACHE is not None and _DAILY_ROWS_CACHE[0]==signature:
            return {symbol:[row for row in _DAILY_ROWS_CACHE[1].get(symbol,[]) if row[0]<=latest_ns]
                for symbol in symbols}
        with closing(sqlite3.connect(uri,uri=True,timeout=5)) as db:
            rows=db.execute("SELECT symbol,stamp_ns,open,high,low,close,volume FROM daily_bars ORDER BY symbol,stamp_ns").fetchall()
    except (sqlite3.Error,OSError):
        return {}
    out=defaultdict(list)
    for symbol,stamp,op,high,low,close,volume in rows:
        out[symbol].append((int(stamp),float(op),float(high),float(low),float(close),float(volume)))
    _DAILY_ROWS_CACHE=(signature,out)
    return {symbol:[row for row in out.get(symbol,[]) if row[0]<=latest_ns] for symbol in symbols}
