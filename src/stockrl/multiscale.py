"""Existing completed daily-bar storage used by LiveMarketCollector."""
from pathlib import Path
import sqlite3
import math
import pandas as pd
from .paths import ensure_project_path
TIMEFRAME_NAMES=("1m","3m","5m","15m","60m","1d","1w","1mo")
DAILY_ENCODER_BARS=1300

class DailyBarStore:
    """Bounded multi-year completed daily OHLCV rows per symbol."""

    MAX_BARS_PER_SYMBOL = 1500

    def __init__(self, path: str | Path):
        self.path = ensure_project_path(path, "multiscale daily bars")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30)
        self.db.execute("PRAGMA auto_vacuum=INCREMENTAL")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA journal_size_limit=4194304")
        self.db.execute("PRAGMA max_page_count=4294967294")
        self.db.execute("""CREATE TABLE IF NOT EXISTS daily_bars (
            symbol TEXT NOT NULL, stamp_ns INTEGER NOT NULL,
            open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
            close REAL NOT NULL, volume REAL NOT NULL,
            PRIMARY KEY(symbol, stamp_ns))""")
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
        with self.db:
            self.db.executemany("""INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(symbol,stamp_ns) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume""", values)
            for symbol in {value[0] for value in values}:
                boundary = self.db.execute(
                    "SELECT stamp_ns FROM daily_bars WHERE symbol=? ORDER BY stamp_ns DESC LIMIT 1 OFFSET ?",
                    (symbol, self.MAX_BARS_PER_SYMBOL - 1)).fetchone()
                if boundary:
                    self.db.execute("DELETE FROM daily_bars WHERE symbol=? AND stamp_ns<?",
                                    (symbol, int(boundary[0])))
        if self.path.stat().st_size > 16 * 1024 * 1024:
            self.db.execute("PRAGMA incremental_vacuum(128)")
        return len(values)

    def close(self) -> None:
        self.db.close()
