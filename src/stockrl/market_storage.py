"""Deduplicated completed bars, persisted through the current official DataStore."""
from __future__ import annotations

import csv
import os
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
    """Append completed bars once without pruning the official price history."""

    def __init__(self, path: str | Path):
        self.path = ensure_project_path(path, "market data")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        from .framework import ROOT,finrlx
        self.store=finrlx('data.data_store').DataStore(str(ROOT/'data'))
        self.processor=finrlx('data.data_processor').DataProcessor(str(self.path.parent/'data'))
        self.db_path=self.store.db_path
        self._seed_index()

    def _seed_index(self) -> None:
        if self.path.exists() and self.path.stat().st_size:
            for chunk in pd.read_csv(self.path,chunksize=100_000):self._save_prices(chunk)

    def _save_prices(self,frame):
        canonical=frame.rename(columns={'symbol':'gvkey','date':'datadate','open':'prcod','high':'prchd','low':'prcld','close':'prccd','volume':'cshtrd'}).copy()
        canonical['ajexdi']=1.
        canonical=self.processor._clean_price_data(canonical)
        canonical['datadate']=canonical.datadate.map(lambda value:value.isoformat())
        return self.store.save_price_data(canonical)

    def append(self, rows: list[dict[str, Any]]) -> int:
        unique: list[dict[str, Any]] = []
        batch: set[tuple[str, int]] = set()
        if not rows:return 0
        stamps=pd.to_datetime([r.get('date') for r in rows],utc=True,errors='coerce',format='mixed')
        valid=[s.value for s in stamps if not pd.isna(s)]
        if not valid:return 0
        symbols=sorted({str(r.get('symbol')) for r in rows if r.get('symbol')})
        existing=set()
        stored=self.store.get_price_data(symbols,min(s.isoformat() for s in stamps if not pd.isna(s)),max(s.isoformat() for s in stamps if not pd.isna(s)))
        if not stored.empty:
            existing={(str(symbol),int(pd.Timestamp(stamp).value)) for symbol,stamp in zip(stored.tic,stored.datadate)}
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
        self._save_prices(pd.DataFrame(unique))
        return len(unique)

    def close(self):
        # Upstream sqlite context managers leave connections for cyclic GC.
        import gc
        gc.collect()
