"""Shared account, reward, replay, market-data and GPU scheduling regressions."""
from pathlib import Path
from contextlib import closing
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json, queue, threading, unittest, sqlite3
import numpy as np
import torch
from stockrl.market_reader import IncrementalMarketCSV
from stockrl.paper_account import PaperAccount
from stockrl.state_io import atomic_json
ROOT=Path(__file__).resolve().parents[1]

class Panel:

    def __init__(self):
        self.dates=np.arange(np.datetime64("2026-09-30T01:00"),np.datetime64("2026-09-30T01:08"),
                             np.timedelta64(1,"m")).astype("datetime64[ns]")
        self.symbols=["TEST.KS","CONTEXT"]
        self.groups={"TEST.KS":("KRX","equity"),"CONTEXT":("FX","currency")}
        self.features=np.zeros((8,2,17),np.float32)
        self.closes=np.asarray([[100+i*2,100] for i in range(8)],dtype=np.float64)
        self.observed=np.ones((8,2),bool)
        self.symbol_ids=np.asarray([0,1]); self.market_ids=np.asarray([0,1]); self.asset_ids=np.asarray([0,1])

class SharedPaperTests(unittest.TestCase):







    def test_reader_never_trims_unprocessed_market_bars(self):
        import pandas as pd
        reader=IncrementalMarketCSV(ROOT/"unused.csv",retain_timestamps=8)
        frame=pd.DataFrame({"date":pd.date_range("2026-09-30",periods=400,freq="min",tz="UTC"),
                            "symbol":["TEST.KS"]*400})
        self.assertEqual(len(reader._trim(frame)),400)
        reader.processed_through=str(frame.date.iloc[200])
        trimmed=reader._trim(frame)
        self.assertEqual(len(trimmed),327) # 128 preceding context + all 199 new bars.
        self.assertEqual(trimmed.date.iloc[-1],frame.date.iloc[-1])

    def test_feed_compaction_preserves_unobserved_bars_and_input_history(self):
        import pandas as pd
        from stockrl.live_feed import AppendOnlyMarketCSV
        with TemporaryDirectory(dir=ROOT) as directory:
            path=Path(directory)/"market.csv"
            (path.parent/"agent").mkdir()
            dates=pd.date_range("2026-09-30",periods=800,freq="min",tz="UTC")
            atomic_json({"last_timestamp":dates[200].isoformat()},path.parent/"agent"/"live_cursor.json")
            writer=AppendOnlyMarketCSV(path); writer.COMPACT_CSV_BYTES=1; writer._next_csv_compaction=1
            try:
                writer.append([{"date":stamp.isoformat(),"symbol":"TEST.KS","market":"KRX",
                    "asset_class":"equity","close":100} for stamp in dates])
            finally:
                writer.close()
            stored=pd.read_csv(path)
            self.assertEqual(len(stored),727)
            self.assertEqual(pd.to_datetime(stored.date,utc=True).iloc[0],dates[73])
            self.assertEqual(pd.to_datetime(stored.date,utc=True).iloc[-1],dates[799])

    def test_reader_preserves_closed_equity_window(self):
        import pandas as pd
        dates=pd.date_range("2026-09-30",periods=400,freq="min")
        active=pd.DataFrame({"date":dates,"symbol":"ACTIVE","asset_class":"equity"})
        closed=pd.DataFrame({"date":dates[:150],"symbol":"CLOSED.KS","asset_class":"equity"})
        reader=IncrementalMarketCSV("unused.csv",retain_timestamps=128)
        reader.processed_through=str(dates[350])
        trimmed=reader._trim(pd.concat([active,closed],ignore_index=True))
        kept=trimmed.loc[trimmed.symbol=="CLOSED.KS"]
        self.assertEqual(len(kept),128)
        self.assertEqual(list(kept.date),list(dates[22:150]))

    def test_feed_compaction_carries_closed_equity_quotes(self):
        import pandas as pd
        from stockrl.live_feed import AppendOnlyMarketCSV
        with TemporaryDirectory(dir=ROOT) as directory:
            path=Path(directory)/"market.csv"; (path.parent/"agent").mkdir()
            dates=pd.date_range("2026-09-30",periods=800,freq="min",tz="UTC")
            atomic_json({"last_timestamp":dates[700].isoformat()},path.parent/"agent"/"live_cursor.json")
            writer=AppendOnlyMarketCSV(path);writer.COMPACT_CSV_BYTES=1;writer._next_csv_compaction=1
            try:
                rows=[{"date":stamp.isoformat(),"symbol":"ACTIVE","market":"US","asset_class":"equity","close":100} for stamp in dates]
                rows += [{"date":stamp.isoformat(),"symbol":"CLOSED.KS","market":"KRX","asset_class":"equity","close":110} for stamp in dates[:200]]
                writer.append(rows)
            finally:
                writer.close()
            kept=pd.read_csv(path).query("symbol=='CLOSED.KS'")
            self.assertEqual(len(kept),128)
            self.assertEqual(list(pd.to_datetime(kept.date,utc=True)),list(dates[72:200]))
            self.assertTrue((kept.close==110).all())


    def test_account_can_add_and_partially_reduce_position(self):
        account=PaperAccount.in_memory(.001,.0001)
        account._fill("TEST.KS","KRW","BUY",100,0,10000,"T1")
        initial=account.state["books"]["KRW"]["positions"]["TEST.KS"]["quantity"]
        account._fill("TEST.KS","KRW","BUY",100,0,5000,"T2")
        added=account.state["books"]["KRW"]["positions"]["TEST.KS"]["quantity"]
        self.assertGreater(added,initial)
        account._fill("TEST.KS","KRW","SELL",110,0,10,"T3")
        self.assertEqual(account.state["books"]["KRW"]["positions"]["TEST.KS"]["quantity"],added-10)

    def test_atomic_state_recovers_from_brief_file_lock(self):
        import os
        replace=os.replace; attempts=[]
        def transient(*args):
            attempts.append(1)
            if len(attempts)<3: raise PermissionError("temporary sharing violation")
            return replace(*args)
        with TemporaryDirectory(dir=ROOT) as directory:
            path=Path(directory)/"account.json"
            with patch("stockrl.state_io.os.replace",side_effect=transient): atomic_json({"ok":True},path)
            self.assertEqual(json.loads(path.read_text()),{"ok":True})
            self.assertFalse(path.with_name("account.json.tmp").exists())










    def test_daily_store_keeps_five_years_and_excludes_unfinished_days(self):
        from stockrl.multiscale import DailyBarStore, _load_daily
        import pandas as pd
        with TemporaryDirectory(dir=ROOT) as directory:
            path=Path(directory)/"daily.sqlite3";store=DailyBarStore(path)
            days=pd.bdate_range("2018-01-01",periods=1600)
            store.upsert([dict(symbol="TEST.KS",date=str(day),open=100+i,
                high=101+i,low=99+i,close=100+i,volume=1000+i) for i,day in enumerate(days)])
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0],1500)
            # The latest row exists in storage but its day has not finished yet.
            stamp=np.datetime64(str(days[-1].date())+"T12:00:00","ns")
            frame=pd.DataFrame([dict(symbol="TEST.KS",date=str(stamp),open=1,high=1,low=1,close=1,volume=1)])
            cutoff=int(days[-2].value)
            history=_load_daily(path,{'TEST.KS'},cutoff)['TEST.KS']
            self.assertEqual(history[-1][4],100+1598)
            self.assertTrue(all(row[0]<=cutoff for row in history))
            earlier=int(days[-20].value)
            self.assertTrue(all(row[0]<=earlier for row in _load_daily(path,{"TEST.KS"},earlier)["TEST.KS"]))
            store.close()

    def test_sor_subscription_is_one_identity_per_stock_and_trade_direction_is_retained(self):
        from stockrl.kiwoom_stream import KiwoomRealtimeStream
        instruments=[{"symbol":f"{i:06d}.KS","market":"KRX","asset_class":"equity"} for i in range(105)]
        with patch("stockrl.kiwoom_stream.read_settings",return_value={"environment":"real"}):
            stream=KiwoomRealtimeStream(ROOT,instruments,threading.Event(),queue.Queue())
        self.assertEqual(len(stream.subscription_codes),105)
        self.assertTrue(all(code.endswith("_AL") for code in stream.subscription_codes))
        for volume in ("+5","-3"):
            stream._on_message({"trnm":"REAL","data":[{"type":"0B","item":"000001_AL",
                "values":{"20":"090000","10":"100","15":volume,"27":"101","28":"99","9081":"2"}}]})
        bar=stream.bars["000001.KS"]
        self.assertEqual((bar["volume"],bar["buy_volume"],bar["sell_volume"]),(8,5,3))
        self.assertEqual(stream.stats["nxt_ticks"],2)
