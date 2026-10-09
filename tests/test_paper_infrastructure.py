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
from stockrl.market_panel import GlobalMarketPanel, MARKET_CONTEXT_FEATURES as CONTEXT_FEATURES
from stockrl.multiscale import MULTISCALE_FEATURE_COUNT
from stockrl.paper_account import PaperAccount
from stockrl.account_diagnostics import summarize_account, summarize_policy
from stockrl.operating_rules import daily_boundary, operating_rules
from stockrl.state_io import atomic_json
ROOT=Path(__file__).resolve().parents[1]

class Panel:
    window=GlobalMarketPanel.window

    def __init__(self):
        self.dates=np.arange(np.datetime64("2026-09-30T01:00"),np.datetime64("2026-09-30T01:08"),
                             np.timedelta64(1,"m")).astype("datetime64[ns]")
        self.symbols=["TEST.KS","CONTEXT"]
        self.groups={"TEST.KS":("KRX","equity"),"CONTEXT":("FX","currency")}
        self.features=np.zeros((8,2,17),np.float32)
        self.closes=np.asarray([[100+i*2,100] for i in range(8)],dtype=np.float64)
        self.observed=np.ones((8,2),bool)
        self.symbol_ids=np.asarray([0,1]); self.market_ids=np.asarray([0,1]); self.asset_ids=np.asarray([0,1])
        self.market_context=np.zeros((8,len(CONTEXT_FEATURES)),np.float32)

    def multiscale_at(self,index):
        return np.full((2,MULTISCALE_FEATURE_COUNT),index,np.float32)

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

    def test_controls_are_independent(self):
        from stockrl.platform.runtime import Runtime
        with TemporaryDirectory() as directory:
            supervisor=Runtime.__new__(Runtime);supervisor.lock=threading.RLock();supervisor.root=Path(directory)
            supervisor.library=type('LibraryStub',(),{'active':False})()
            supervisor.controls={'feed':True,'engine':True,'paper':True,'learning':True,'mode':'live'}
            supervisor.retries={'feed':(5,0),'learner':(3,0)}
            result=supervisor.command('feed',False)['controls']
            self.assertFalse(result['feed']);self.assertTrue(result['paper']);self.assertTrue(result['learning'])
            supervisor.command('paper',False);supervisor.command('learning',False)
            result=supervisor.command('paper',True)['controls']
            self.assertFalse(result['feed']);self.assertFalse(result['learning']);self.assertTrue(result['paper'])
            self.assertEqual(supervisor.retries['feed'][0],5)
            self.assertEqual(supervisor.retries['learner'][0],3)
            supervisor.command('learning',True)
            self.assertNotIn('learner',supervisor.retries)
            self.assertIn('feed',supervisor.retries)
            result=supervisor.command('engine',False)['controls']
            self.assertFalse(result['paper'])




    def test_git_split_sqlite_restores_complete_pending_work_without_overwriting_live_db(self):
        from stockrl.runtime_backup import restore_sqlite_backup
        import sqlite3,gzip,json,hashlib
        with TemporaryDirectory(dir=ROOT) as directory:
            path=Path(directory)/"replay.sqlite3"
            with closing(sqlite3.connect(":memory:")) as db:
                db.execute("CREATE TABLE pending_records (value TEXT)")
                db.execute("INSERT INTO pending_records VALUES ('unlearned')");db.commit()
                content=db.serialize()
            parts=[]
            for index,start in enumerate(range(0,len(content),2048)):
                name=path.name+".part%03d.gz"%index
                (path.parent/name).write_bytes(gzip.compress(content[start:start+2048]))
                parts.append({"name":name})
            path.with_name(path.name+".restore.json").write_text(json.dumps({
                "parts":parts,"bytes":len(content),"sha256":hashlib.sha256(content).hexdigest()}))
            self.assertTrue(restore_sqlite_backup(path))
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("SELECT value FROM pending_records").fetchone()[0],"unlearned")
            before=path.read_bytes()
            self.assertFalse(restore_sqlite_backup(path))
            self.assertEqual(path.read_bytes(),before)
            self.assertFalse(path.with_name(path.name+".restore.tmp").exists())

    def test_goal_win_is_once_per_currency_persistent_and_reset_is_explicit(self):
        with TemporaryDirectory(dir=ROOT) as directory:
            account=PaperAccount(Path(directory)/"account.json",0,0)
            initial=account.state["books"]["KRW"]["cash"]
            episode=account.state["episode_id"]
            account.configure_goal()
            self.assertEqual(account.state["books"]["KRW"]["cash"],initial)
            self.assertEqual(account.goal_inputs(),[1,1,10,.9,.9,1])
            account.state["books"]["KRW"]["cash"]=initial*10
            account.observe_goal("T1");account.save()
            loaded=PaperAccount(account.path,0,0);loaded.configure_goal();loaded.observe_goal("T2")
            self.assertEqual(loaded.goal_points(),{"KRW":100,"USD":0})
            self.assertEqual(loaded.goal_summary()["books"]["KRW"]["win"]["timestamp"],"T1")
            self.assertEqual(loaded.reward_points()["KRW"],900)
            loaded.state["books"]["USD"]["cash"]=100_000
            loaded.observe_goal("T3")
            self.assertEqual(loaded.goal_summary()["status"],"WIN")
            loaded.reset()
            self.assertNotEqual(loaded.state["episode_id"],episode)
            self.assertEqual(loaded.goal_points(),{"KRW":0,"USD":0})
            self.assertEqual(loaded.goal_summary()["target_multiple"],10)




    def test_daily_store_keeps_five_years_and_excludes_unfinished_days(self):
        from stockrl.multiscale import DailyBarStore, MultiscaleFeatures, _load_daily
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
            features=MultiscaleFeatures(frame,["TEST.KS"],path,stamp)
            history=features.daily_at(stamp)
            self.assertEqual(history.shape,(1,1300,6))
            self.assertEqual(float(history[...,5].sum()),1300)
            self.assertLess(features.bars[("TEST.KS","1d")][0][-2],int(stamp.astype(np.int64)))
            expected_last_close=100+1598
            last_return=100*(expected_last_close/(100+1597)-1)
            self.assertAlmostEqual(float(history[0,-1,3]),last_return,places=3)
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
