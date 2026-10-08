"""Portfolio-contract, actual MoE state, TorchRL learning and crash recovery regressions."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import torch
from tensordict import TensorDict
from strategies.base_strategy import StrategyResult

from stockrl.platform.policy import build_policy,observation,decide,parameters,INPUT_KEYS,MoETrunk
from stockrl.platform.model_asset import load_moe_head,validate_source
from stockrl.platform.config import LearningSettings,RiskSettings,Settings
from stockrl.platform.learner import learn_batch
from stockrl.platform.journal import Journal
from stockrl.platform.checkpoint import Checkpoints
from stockrl.platform.weights import risk_overlay,evaluate_recorded_weights
from stockrl.platform.observations import prepare_evidence,native_input
from stockrl.platform.environment import PortfolioEnvironment,market_view


def spec():
    return {"expert_ids":["chronos","macrophft_slope_1"],"config":{
        "feature_sizes":{"chronos":4,"macrophft_slope_1":5},"stock_policy_ids":[]},"source_updates":9}


def obs(n=2):
    return observation({"chronos":np.ones((n,4),np.float32),"macrophft_slope_1":np.ones((n,5),np.float32)},
                       np.ones((n,2),bool),np.zeros((n,16)),np.zeros((n,8)),
                       {"macrophft_slope_1":np.array([[.1,.9]]*n,np.float32)})


class MoEPolicyTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(2); torch.manual_seed(4)

    def test_existing_head_is_exact_initial_state_and_asset_is_unchanged(self):
        model_spec=spec(); original=MoETrunk(model_spec).state_dict()
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'champion.pt'
            torch.save({"format":"registered_vertical_trading_moe_v1","config":model_spec["config"],
                "state_dict":original,"expert_mapping":{k:{} for k in model_spec["expert_ids"]},"optimizer_updates":9},file)
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            loaded,state=load_moe_head(file); actor,critic=build_policy(loaded,state)
            trunk=next(m for m in actor.modules() if isinstance(m,MoETrunk))
            for name,value in original.items():
                torch.testing.assert_close(trunk.state_dict()[name],value,rtol=0,atol=0)
            self.assertEqual(loaded['source_updates'],9)
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),digest)
            self.assertFalse(any(name.startswith('experts.') for name,_ in actor.named_parameters()))

    def test_torchrl_updates_real_moe_and_accepts_variable_asset_count(self):
        actor,critic=build_policy(spec()); initial=next(actor.parameters()).detach().clone(); rows=[]
        for i in range(8):
            weights,td=decide(actor,critic,obs(),explore=True)
            self.assertAlmostEqual(float(weights.sum()),1,places=5)
            row=td.select(*INPUT_KEYS,'action','action_log_prob','state_value').to_dict()
            row['next']={**obs().to_dict(),'reward':torch.tensor([.01*i]),'done':torch.tensor([False])}
            rows.append(row)
        optimizer=torch.optim.AdamW(parameters(actor,critic),lr=.001)
        loss,steps=learn_batch(actor,critic,optimizer,rows,LearningSettings(batch_size=8,epochs=2))
        self.assertTrue(np.isfinite(loss)); self.assertGreater(steps,0)
        self.assertFalse(torch.equal(initial,next(actor.parameters())))
        self.assertEqual(decide(actor,critic,obs(5),explore=False)[0].shape,(6,))
        self.assertEqual(len(parameters(actor,critic)),len({id(p) for p in parameters(actor,critic)}))

    def test_future_and_missing_native_inputs_are_not_relabelled(self):
        packet={"expert":"chronos","as_of":"2026-01-02","symbols":["A"],"native_output":[[.1]],
                "layout":"symbol,horizon","horizon":1,"sampling_seconds":86400}
        _,mask,_=prepare_evidence({'chronos':[packet]},['A'],spec(),'2026-01-01')
        self.assertFalse(mask.any())
        for key in ('marketgpt','macrophft_slope_1'):
            with self.assertRaises(ValueError): native_input(key,pd.DataFrame(),pd.DataFrame(),'2026-01-01')

    def test_resume_rejects_other_moe_assets_but_allows_machine_path_change(self):
        saved={"expert_ids":['chronos'],"config":{},"source_head_sha256":'one',"source_model_bytes":100,
               "source_model":'C:/Users/old/Desktop/model/champion.pt'}
        selected={**saved,"source_model":'C:/Users/new/Desktop/model/champion.pt'}
        validate_source(saved,selected)
        with self.assertRaises(ValueError):validate_source(saved,{**selected,'source_head_sha256':'another'})


class DurableOperationsTests(unittest.TestCase):
    def test_requested_stop_is_not_reported_as_a_process_failure(self):
        from unittest.mock import Mock
        from stockrl.platform.runtime import Runtime
        import threading
        with tempfile.TemporaryDirectory() as directory:
            runtime=Runtime.__new__(Runtime)
            runtime.root=Path(directory);runtime.settings=Settings();runtime.lock=threading.RLock()
            runtime.controls={"feed":False,"engine":False,"paper":False,"learning":False}
            runtime.children={'feed':object()};runtime.retries={'feed':(1,0)};runtime.journal=Mock()
            runtime.process=lambda role:None
            runtime.closing=Mock();runtime.closing.wait.side_effect=[False,True]
            runtime._monitor()
            self.assertFalse(runtime.children);self.assertFalse(runtime.retries)
            runtime.controls['feed']=True;runtime.spawn=Mock()
            runtime.closing.wait.side_effect=[False,True]
            runtime._monitor()
            runtime.spawn.assert_called_once_with('feed')
            runtime.journal.event.assert_not_called()

    def test_recorded_weights_rebalance_intraday_on_next_observation(self):
        dates=pd.date_range('2026-01-01',periods=4,freq='min')
        prices=pd.DataFrame({'A':[100,110,121,121]},index=dates)
        weights=pd.DataFrame({'A':[.5,0,0,0]},index=dates)
        result=evaluate_recorded_weights(prices,weights,0,10000)
        self.assertAlmostEqual(result['return_rate'],.05,places=6)
        self.assertAlmostEqual(result['final_nav'],10500,places=4)
        with_costs=evaluate_recorded_weights(prices,weights,.001,10000)
        self.assertLess(with_costs['return_rate'],result['return_rate'])

    def test_notification_read_watermark_preserves_new_events(self):
        with tempfile.TemporaryDirectory() as directory:
            journal=Journal(Path(directory)/'ops.sqlite3')
            journal.event('error','first')
            through=journal.events()[0]['id']
            journal.event('error','arrived while panel opened')
            journal.read_events(through)
            events=journal.events()
            self.assertFalse(events[0]['read'])
            self.assertTrue(events[1]['read'])
            journal.close()

    def test_settlement_and_account_are_one_recoverable_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ops.sqlite3'; journal=Journal(path)
            journal.set_state('account',{'equity':100})
            journal.replace_pending('USD',{'as_of':'one'})
            with self.assertRaises(RuntimeError),journal.transaction():
                journal.set_state('account',{'equity':99})
                journal.settle('USD','A',0,{'x':torch.ones(1)})
                raise RuntimeError('simulated crash')
            journal.close(); journal=Journal(path)
            self.assertEqual(journal.get_state('account')['equity'],100)
            self.assertEqual(journal.pending()['USD']['as_of'],'one')
            self.assertEqual(journal.stats()['total'],0)
            journal.close()

    def test_checkpoint_restore_checksum_rollback_and_applied_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            actor,critic=build_policy(spec()); optimizer=torch.optim.AdamW(parameters(actor,critic),lr=.001)
            checkpoints=Checkpoints(Path(directory),retain=3)
            first=checkpoints.save(actor,critic,optimizer,1,spec()['expert_ids'],[4,5],optimizer_steps=10)
            second=checkpoints.save(actor,critic,optimizer,2,spec()['expert_ids'],[6],optimizer_steps=20)
            state,_=checkpoints.load()
            self.assertEqual(state['applied_ids'],[6]); self.assertEqual(state['optimizer_steps'],20)
            checkpoints.rollback(first['file']); self.assertEqual(checkpoints.load()[0]['version'],1)
            path=Path(directory)/first['file']; path.write_bytes(path.read_bytes()+b'bad')
            with self.assertRaises(ValueError): checkpoints.load(recover=False)
            recovered,record=checkpoints.load()
            self.assertEqual(recovered['version'],2)
            self.assertEqual(record['recovered_from'],first['file'])

    def test_risk_caps_and_unobserved_holdings(self):
        risk=RiskSettings(max_asset_weight=.3,max_exposure=.9,max_turnover=.2)
        weights,_=risk_overlay([.8,.8],[.7,0],[False,True],risk)
        self.assertAlmostEqual(weights[0],.7)
        self.assertLessEqual(weights.sum(),.900001)
        self.assertLessEqual(abs(weights-np.array([.7,0])).sum(),.200001)
        weights,info=risk_overlay([.2],[.3],[True],risk,drawdown=.2)
        self.assertEqual(weights[0],0); self.assertTrue(info['blocked_reason'])

    def test_next_bar_fill_and_costs_enter_portfolio_reward(self):
        with tempfile.TemporaryDirectory() as directory:
            journal=Journal(Path(directory)/'ops.sqlite3')
            settings=SimpleNamespace(state_dir=Path(directory),risk=RiskSettings(max_asset_weight=.5,max_turnover=.5),
                                     learning=LearningSettings(),enabled_experts=[],resources=SimpleNamespace(market_refresh_seconds=300))
            env=PortfolioEnvironment(settings,journal,spec())
            frame=pd.DataFrame([{'date':f'2026-01-01T00:0{i}:00','symbol':'A','market':'US','asset_class':'equity',
                                 'open':100,'high':110,'low':99,'close':100+i,'volume':1000} for i in range(3)])
            view,frame=market_view(frame)
            packet={'expert':'chronos','as_of':str(view.dates[0]),'symbols':['A'],'native_output':[[.01]],
                    'layout':'symbol,horizon','horizon':1,'sampling_seconds':86400}
            env.advance(view,0,True); data=env.observe(view,frame,0,'USD',{'chronos':[packet]})
            actor,critic=build_policy(spec()); _,transition=decide(actor,critic,data['observation'],explore=True)
            result=StrategyResult('test',pd.DataFrame({'gvkey':['A'],'weight':[.5]}),
                                  {'transition':transition,'risk':{'cash_weight':.5}})
            env.submit(result,data,view,0,0,True)
            self.assertEqual(env.account.snapshot()['books']['USD']['trade_count'],0)
            fills=env.advance(view,1,True); self.assertTrue(fills)
            next_data=env.observe(view,frame,1,'USD',{'chronos':[packet]})
            env.settle(next_data,0)
            self.assertEqual(journal.stats()['total'],1)
            row=journal.db.execute('SELECT payload FROM transitions').fetchone()[0]
            from stockrl.platform.journal import decode
            reward=decode(row)['next']['reward'].item()
            self.assertLess(reward,0)
            journal.close()


if __name__=='__main__': unittest.main()
