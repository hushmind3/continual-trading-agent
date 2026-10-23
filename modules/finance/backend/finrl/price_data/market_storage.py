"""Deduplicated live bars kept separate from the official daily price history."""
from __future__ import annotations

import csv
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pandas as pd

from ...paths import ensure_project_path

FEED_COLUMNS = [
    "date", "symbol", "source", "timeframe", "market", "asset_class", "open", "high", "low", "close", "volume",
    "bid", "ask", "bid_size", "ask_size", "buy_volume", "sell_volume", "trade_count",
    "implied_volatility", "open_interest", "yield_change", "days_to_expiry",
]


class AppendOnlyMarketCSV:
    """Append completed bars once without pruning the official price history."""

    def __init__(self, path: str | Path):
        self.path = ensure_project_path(path, "market data")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        from ... import ROOT
        from .operations import price_store
        self.store=price_store(ROOT/'data')
        self.db_path=self.store.db_path
        self.raw_path=self.path.with_name("timeframes.sqlite3")
        self.last_added_rows=[]
        with closing(sqlite3.connect(self.raw_path)) as db,db:
            db.execute("CREATE TABLE IF NOT EXISTS received_bars (symbol TEXT NOT NULL, stamp_ns INTEGER NOT NULL, PRIMARY KEY(symbol,stamp_ns))")
        self._seed_index()

    def _seed_index(self) -> None:
        if self.path.exists() and self.path.stat().st_size:
            with closing(sqlite3.connect(self.raw_path)) as db,db:
                for chunk in pd.read_csv(self.path,chunksize=100_000):
                    stamps=pd.to_datetime(chunk.date,utc=True,errors='raise',format='mixed')
                    db.executemany("INSERT OR IGNORE INTO received_bars VALUES (?,?)",zip(chunk.symbol.astype(str),stamps.astype('int64').map(int)))

    def _save_prices(self,frame):
        if frame.empty:return 0
        canonical=frame.rename(columns={'symbol':'gvkey','date':'datadate','open':'prcod','high':'prchd','low':'prcld','close':'prccd','volume':'cshtrd'}).copy()
        canonical['ajexdi']=1.
        from .storage import clean_price_data
        canonical=clean_price_data(canonical)
        canonical['datadate']=canonical.datadate.map(lambda value:value.isoformat())
        return self.store.save_price_data(canonical)

    def append(self, rows: list[dict[str, Any]]) -> int:
        self.last_added_rows=[]
        unique=[];batch=set()
        if not rows:return 0
        stamps=pd.to_datetime([r.get('date') for r in rows],utc=True,errors='coerce',format='mixed')
        with closing(sqlite3.connect(self.raw_path)) as db,db:
            for source,stamp in zip(rows,stamps):
                row={key:source.get(key) for key in FEED_COLUMNS}
                if pd.isna(stamp) or not row['symbol']:continue
                row['source']=source.get('source') or source.get('provider') or 'unknown'
                row['timeframe']=source.get('timeframe') or '1m'
                key=(str(row['symbol']),int(stamp.value))
                if key in batch:continue
                inserted=db.execute("INSERT OR IGNORE INTO received_bars VALUES (?,?)",key).rowcount
                if not inserted:continue
                batch.add(key);row['date']=stamp.isoformat();unique.append(row)
            if not unique:return 0
            if self._save_prices(pd.DataFrame(unique))!=len(unique):
                raise ValueError('완료 시세의 가격 저장 개수가 수신 봉과 다릅니다.')
            fresh=not self.path.exists() or self.path.stat().st_size==0
            columns=FEED_COLUMNS
            if not fresh:
                with self.path.open(newline='',encoding='utf8') as existing:columns=next(csv.reader(existing))
            with self.path.open('a',newline='',encoding='utf8') as stream:
                writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore')
                if fresh:writer.writeheader()
                writer.writerows(unique);stream.flush();os.fsync(stream.fileno())
        self.last_added_rows=unique
        return len(unique)

    def close(self):
        # Upstream sqlite context managers leave connections for cyclic GC.
        import gc
        gc.collect()
