import tempfile
import unittest
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from stockrl.moe_paper import TradingMoEPaper


def panel():
    return SimpleNamespace(dates=np.array(["2025-10-29T14:00","2025-10-29T14:01","2025-10-29T15:02"],dtype="datetime64[ns]"),
        symbols=["AAPL"],groups={"AAPL":("US","equity")},observed=np.ones((3,1),bool),
        closes=np.array([[100.],[101.],[102.]]),features=np.zeros((3,1,17),np.float32),
        symbol_ids=np.array([0]),market_ids=np.array([0]),asset_ids=np.array([0]))


class PaperBridgeTests(unittest.TestCase):
    def test_context_filter_precedes_fifo_limit_without_deleting_old_rows(self):
        self.bridge.advance(self.panel,0)
        self.bridge.submit(self.result,self.panel,0,paper_executable=True)
        self.bridge.advance(self.panel,1);self.bridge.advance(self.panel,2)
        old = self.bridge.replay.pending_batch(1)[0]
        ready = deepcopy(old)
        ready.timestamp = "2025-10-30T14:00:00.000000000"
        self.bridge.replay.add(ready)
        total = self.bridge.replay.stats()["total"]
        selected = self.bridge.replay.pending_batch(1,timestamps={ready.timestamp})
        self.assertEqual([e.timestamp for e in selected],[ready.timestamp])
        self.assertEqual(self.bridge.replay.pending_batch(1)[0].timestamp,old.timestamp)
        self.assertEqual(self.bridge.replay.stats()["total"],total)
        self.assertEqual(self.bridge.replay.pending_batch(1,timestamps=set()),[])

    def test_paper_off_cancels_orders_without_erasing_positions_or_learning(self):
        self.bridge.advance(self.panel,0)
        self.bridge.submit(self.result,self.panel,0,paper_executable=True)
        self.assertTrue(self.bridge.paper_account.state["pending"])
        self.assertEqual(self.bridge.advance(self.panel,1,enabled=False),[])
        self.assertFalse(self.bridge.paper_account.state["pending"])
        self.assertEqual(self.bridge.paper_account.state["books"]["USD"]["cash"],10000)

    def test_current_worker_reads_independent_operator_flags(self):
        from stockrl.platform.worker_state import control
        settings=SimpleNamespace(state_dir=Path(self.temp.name))
        self.assertEqual(control(settings),{'paper':False,'learning':True})
        for paper in (False,True):
            for learning in (False,True):
                expected=dict(feed=True,engine=True,paper=paper,learning=learning,mode='live')
                (settings.state_dir/'control.json').write_text(json.dumps(expected))
                self.assertEqual(control(settings),expected)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.bridge=TradingMoEPaper(Path(self.temp.name));self.panel=panel()
        self.result={"as_of":str(self.panel.dates[0]),"trading_output":{"executable":False,
            "actions":{"AAPL":"BUY"},"target_weights":{"AAPL":.4},"cash_weights_by_currency":{"USD":.6}}}

    def tearDown(self):self.temp.cleanup()

    def test_paper_guard_and_live_guard(self):
        self.bridge.advance(self.panel,0)
        self.assertFalse(self.bridge.submit(self.result,self.panel,0)["paper_executable"])
        self.assertFalse(self.bridge.paper_account.state["pending"])
        self.bridge.submit(self.result,self.panel,0,paper_executable=True)
        self.assertFalse(self.result["trading_output"]["executable"])
        self.assertFalse(self.bridge.advance(self.panel,0))
        self.assertEqual(len(self.bridge.advance(self.panel,1)),1)
        self.bridge.advance(self.panel,2)
        self.assertLess(self.bridge.paper_account.state["books"]["USD"]["cash"],10000)
        self.assertEqual(self.bridge.replay.stats()["total"],2)
        self.assertEqual(self.bridge.replay.stats()["unsupported"],0)

    def test_pending_survives_restart(self):
        self.bridge.advance(self.panel,0);self.bridge.submit(self.result,self.panel,0,paper_executable=True)
        loaded=TradingMoEPaper(Path(self.temp.name))
        self.assertEqual(len(loaded.pending),1)
        self.assertEqual(len(loaded.advance(self.panel,1)),1)
        loaded.advance(self.panel,2)
        self.assertEqual(loaded.replay.stats()["total"],2)

    def test_stale_asof_rejected(self):
        with self.assertRaises(ValueError):self.bridge.submit(self.result,self.panel,1,paper_executable=True)

    def test_invalid_allocation_rejected(self):
        self.result["trading_output"]["target_weights"]["AAPL"]=-1
        with self.assertRaises(ValueError):self.bridge.submit(self.result,self.panel,0,paper_executable=True)




from contextlib import closing
import sqlite3
from unittest.mock import patch
from stockrl.state_io import EvidenceJournal, append_log, retire_trial_debug, WorkerLog, evidence_status

class RuntimeStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = EvidenceJournal(self.root)
        self.packet = {"expert": "timesfm", "as_of": "2026-10-01", "output_shape": [1, 10000],
                       "native_output": [1.25] * 10000}
        self.decision = {"as_of": "2026-10-01", "raw_outputs": [self.packet],
                         "trading_output": {"actions": {"MSFT": "BUY"}, "target_weights": {"MSFT": .5}}}
        self.contexts = {"2026-10-01": ({"symbols": ["MSFT"], "expert_inputs": {"large": [1] * 1000}}, self.decision)}

    def tearDown(self):
        self.temp.cleanup()

    def test_pending_evidence_survives_restart_and_checkpoint_gate(self):
        self.journal.save_contexts(self.contexts)
        self.journal.save_contexts({})  # update finished, checkpoint not yet saved
        restored = EvidenceJournal(self.root).load_contexts()
        self.assertEqual(restored["2026-10-01"][1]["raw_outputs"], [self.packet])
        self.assertEqual(restored["2026-10-01"][0]["symbols"], ["MSFT"])
        self.assertNotIn("expert_inputs", restored["2026-10-01"][0])
        self.journal.save_contexts({}, checkpoint_saved=True)
        self.assertEqual(self.journal.load_contexts(), {})

    def test_cache_status_reads_counts_without_changing_evidence(self):
        self.journal.save_contexts(self.contexts)
        self.journal.save_market([self.packet])
        self.journal.record_cycle({"timestamp": "2026-10-01", "decision": self.decision})
        before = self.journal.path.read_bytes()
        status = evidence_status(self.root)
        self.assertTrue(status["available"])
        self.assertEqual(status["market_outputs"], 1)
        self.assertEqual(status["stored_outputs"], 1)
        self.assertEqual(status["stored_decisions"], 1)
        self.assertEqual(status["cycles"], 1)
        self.assertEqual(status["latest_as_of"], "2026-10-01")
        self.assertGreater(status["bytes"], 0)
        self.assertEqual(self.journal.path.read_bytes(), before)
        self.assertEqual(self.journal.load_contexts()["2026-10-01"][1]["raw_outputs"], [self.packet])

    def test_cache_status_does_not_create_missing_storage(self):
        missing = self.root / "unused_model"
        self.assertEqual(evidence_status(missing), {"available": False})
        self.assertFalse(missing.exists())

    def test_raw_outputs_are_stored_once_and_cycle_summaries_are_small(self):
        self.journal.save_contexts(self.contexts)
        self.journal.save_market([self.packet])
        for stamp in ("2026-10-01", "2026-10-02"):
            summary = self.journal.record_cycle({"timestamp": stamp, "decision": self.decision})
            self.assertNotIn("raw_outputs", summary["decision"])
        with closing(sqlite3.connect(self.journal.path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM packets").fetchone()[0], 1)
        self.assertLess((self.root / "cycles.jsonl").stat().st_size, 2000)
        self.assertEqual(EvidenceJournal(self.root).cached_rows()[0]["decision"]["raw_outputs"], [self.packet])

    def test_cache_eviction_never_deletes_pending_evidence(self):
        self.journal.save_contexts(self.contexts)
        for index in range(70):
            self.journal.record_cycle({"timestamp": f"{index:03d}", "decision": None})
        self.assertEqual(len(self.journal.cached_rows()), 64)
        self.assertEqual(self.journal.load_contexts()["2026-10-01"][1]["raw_outputs"], [self.packet])

    def test_legacy_context_migrates_with_identical_raw_output(self):
        snapshot, decision = self.contexts["2026-10-01"]
        (self.root / "pending_contexts.json").write_text(json.dumps({"2026-10-01": {
            "snapshot": snapshot, "trading_output": decision["trading_output"], "raw_outputs": decision["raw_outputs"]}}))
        self.journal.migrate_legacy_contexts()
        restored = self.journal.load_contexts()["2026-10-01"][1]
        self.assertEqual(restored["raw_outputs"], decision["raw_outputs"])
        self.assertEqual(restored["trading_output"], decision["trading_output"])

    def test_jsonl_rotation_has_one_backup(self):
        path = self.root / "cycles.jsonl"
        for index in range(100):
            append_log(path, {"index": index}, max_bytes=100)
        self.assertLessEqual(path.stat().st_size, 100)
        self.assertLessEqual(path.with_name("cycles.jsonl.1").stat().st_size, 100)
        self.assertEqual(len(list(self.root.glob("cycles.jsonl*"))), 2)

    def test_worker_output_rotates_during_execution(self):
        path = self.root / "activity.log"
        log = WorkerLog(path)
        with patch("stockrl.state_io.LOG_BYTES", 100):
            self.assertEqual(log.write("x" * 250), 250)
        self.assertLessEqual(path.stat().st_size, 100)
        self.assertLessEqual(path.with_name("activity.log.1").stat().st_size, 100)

    def test_finished_trial_cleanup_preserves_books_replay_and_state(self):
        trial = self.root / "trial"
        trial.mkdir()
        for name in ("paper_account.json", "replay.sqlite3", "optimizer.pt", "decisions.jsonl", "progress.json"):
            (trial / name).write_bytes(b"preserve")
        retire_trial_debug(trial, self.root / "trash")
        for name in ("paper_account.json", "replay.sqlite3", "optimizer.pt"):
            self.assertEqual((trial / name).read_bytes(), b"preserve")
        self.assertFalse((trial / "decisions.jsonl").exists())


if __name__=="__main__":unittest.main()
