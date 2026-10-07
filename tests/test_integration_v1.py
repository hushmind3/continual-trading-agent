"""Focused integration checks; synthetic fixtures never enter operational storage."""
import importlib.util
import sys
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch
from torch import nn

from stockrl.moe_live import LiveInputStream, live_snapshot
from stockrl.moe_paper import TradingMoEPaper
from stockrl.trading_moe import TradingMoE
from stockrl.moe_stock_policies import StockPolicyExpert
from stockrl.paths import DEFAULT_MODEL_DIR,EXPERT_ASSETS_DIR
from stockrl.moe_promotion import (save_runtime_state,load_runtime_state,trainable_path,
    snapshot_pair,promote,rollback,training_state)

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('integration_native_runner',ROOT/'scripts/run_native_vertical_trading.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class FixtureExpert(nn.Module):
    def __init__(self):
        super().__init__();self.weight=nn.Parameter(torch.ones(1));self.entry={'backend':'fixture'}

    def forward(self,root,data,device):
        return dict(native_output=[[float(v[-1])] for v in data['series']],symbols=data['symbols'],
            as_of=data['as_of'],layout='symbol,horizon',units='price',horizon=1,sampling_seconds=60,
            frozen=True,input_shapes={'series':list(np.shape(data['series']))},output_shape=[len(data['symbols']),1])


def fixture_model(root):
    return TradingMoE({'fincast':FixtureExpert(),'macrophft_slope_1':FixtureExpert()},
        {'feature_sizes':{'fincast':4,'macrophft_slope_1':5}},
        {'macro_input_adapter':{'single_features':['s'+str(j) for j in range(36)],
          'trend_features':['t'+str(j) for j in range(9)],'reset_source':'def reset(self):\n    pass'}},root)


def bars(count=35):
    return pd.DataFrame([dict(date=str(pd.Timestamp('2026-10-07T14:00')+pd.Timedelta(minutes=j)),
        symbol='AAPL',market='US',asset_class='equity',open=100+j,high=101+j,low=99+j,close=100+j,volume=1000+j)
        for j in range(count)])


class LiveIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.market=self.root/'market.csv';self.frame=bars();self.frame.to_csv(self.market,index=False)
    def tearDown(self):self.temp.cleanup()

    def test_live_stream_uses_latest_then_new_bars_without_future_input(self):
        stream=LiveInputStream(self.market)
        frame,stamp=stream.next_frame()
        self.assertEqual(stamp,pd.Timestamp(self.frame.date.iloc[-1]))
        self.assertIsNone(stream.next_frame())
        bars(37).iloc[-2:].to_csv(self.market,index=False,header=False,mode='a')
        frame,stamp=stream.next_frame()
        self.assertEqual(stamp,pd.Timestamp(bars(37).date.iloc[-2]))
        self.assertLessEqual(frame.date.max(),stamp)

    def test_native_missing_inputs_are_explicit_and_never_archival(self):
        model=fixture_model(self.root);paper=TradingMoEPaper(self.root/'account').paper_account
        frame=self.frame.copy();frame.date=pd.to_datetime(frame.date)
        panel,index,snapshot,account=live_snapshot(model,self.market,frame,frame.date.iloc[-1],paper)
        self.assertEqual(snapshot['expert_inputs']['fincast']['series'][0][-1],134)
        self.assertEqual(snapshot['input_status']['macrophft_slope_1']['status'],'blocked')
        self.assertNotIn('marketgpt',snapshot['expert_inputs'])
        self.assertEqual(account.shape,(1,1,16))

    def test_live_inference_fill_reward_learning_and_checkpoint_ack(self):
        model=fixture_model(self.root);frozen=model.experts['fincast'].weight.detach().clone()
        optimizer=torch.optim.AdamW(model.parameter_groups(),lr=1e-4)
        state=self.root/'state';bridge=TradingMoEPaper(state,credit_seconds=1)
        args=SimpleNamespace(market=self.market,state=state,root=self.root,checkpoint=self.root/'fixture.pt',
            continuous=False,steps=3,resume=True,interval=.1,device='cpu',recipe=None)
        counter=[35]
        def append(_):
            counter[0]+=1
            bars(counter[0]).iloc[-1:].to_csv(self.market,index=False,header=False,mode='a')
        with patch.object(runner.time,'sleep',side_effect=append),patch.object(pd,'read_feather',side_effect=AssertionError('historical input in live mode')):
            runner.run_live(args,model,optimizer,bridge)
        self.assertGreater(bridge.paper_account.state['books']['USD']['trade_count'],0)
        self.assertGreater(model.optimizer_updates,0)
        self.assertTrue(torch.equal(frozen,model.experts['fincast'].weight))
        self.assertTrue(args.checkpoint.exists())
        self.assertEqual(bridge.replay.stats()['eligible'],0)
        status=json.loads((state/'worker_status.json').read_text())
        self.assertEqual(status['source_kind'],'live')
        self.assertEqual(status['decision']['symbol'],'AAPL')


class StockPolicyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=DEFAULT_MODEL_DIR/'experts/action/stock/verified-policies.pt'
        if not path.exists():raise unittest.SkipTest('local original stock policy weights unavailable')
        cls.saved=torch.load(path,map_location='cpu',weights_only=True)
        cls.native=json.loads((EXPERT_ASSETS_DIR/'stock-policies/native-inputs.json').read_text(encoding='utf-8'))

    def test_all_six_original_policies_execute_and_stay_frozen(self):
        executed=[]
        for key,entry in self.saved['entries'].items():
            expert=StockPolicyExpert.restore(entry,self.saved['states'][key])
            before={k:v.clone() for k,v in expert.state_dict().items()}
            output=expert(None,self.native[key],'cpu')
            self.assertTrue(output['native_features_verified']);self.assertTrue(output['common_output'])
            for name,value in expert.state_dict().items():self.assertTrue(torch.equal(before[name],value),key)
            executed.append(key)
        self.assertEqual(len(executed),6)

    def test_live_history_and_account_build_each_native_observation(self):
        universe=sorted({s for e in self.saved['entries'].values() for s in e['stock_policy']['universe']})
        records=[]
        # Native preprocessing integration fixture, explicitly test-only.
        dates=pd.bdate_range('2025-01-01',periods=180)
        for j,symbol in enumerate(universe):
            for i,day in enumerate(dates):
                price=100+j+i*.1+np.sin(i/3)
                records.append(dict(date=str(day),symbol=symbol,open=price-.2,high=price+1,low=price-1,
                    close=price,volume=10000+10*i+i%7,llm_sentiment=3.,llm_risk=3.))
        for key,entry in self.saved['entries'].items():
            expert=StockPolicyExpert.restore(entry,self.saved['states'][key])
            snapshot=dict(as_of=str(dates[-1]),symbols=universe,stock_policy_history=records,
                policy_account=dict(cash=10000.,nav=10000.,positions={}))
            data=expert.prepare_input(snapshot)
            self.assertIsNotNone(data,(key,expert.input_error))
            output=expert(None,data,'cpu')
            self.assertTrue(output['common_output'],key)
            self.assertEqual(len(data['observations'][0]),entry['stock_policy']['observation_size'])

    def test_missing_universe_is_reported_in_runtime_status(self):
        with tempfile.TemporaryDirectory() as temp:
            model=fixture_model(Path(temp))
            entry=self.saved['entries']['stock_finrl_ppo']
            model.experts['stock_finrl_ppo']=StockPolicyExpert.restore(entry,self.saved['states']['stock_finrl_ppo'])
            model.config['stock_policy_ids']=['stock_finrl_ppo']
            snapshot=dict(symbols=['AAPL'],as_of='2026-10-07',currencies={'AAPL':'USD'},current_weights={'AAPL':0.},
                expert_inputs={},stock_policy_history=[dict(date='2026-10-06',symbol='AAPL',close=100.,open=100.,high=101.,low=99.,volume=1000)],
                policy_account=dict(cash=10000.,nav=10000.,positions={}))
            with torch.no_grad():result,_=model(snapshot,torch.zeros(1,1,16))
            status=result['expert_status']['stock_finrl_ppo']
            self.assertEqual(status['status'],'blocked')
            self.assertIn('missing trained-universe',status['reason'])


class PromotionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.champion=self.root/'champion.pt';self.candidate=self.root/'candidate.pt'
        self.model=fixture_model(self.root)
        self.optimizer=torch.optim.AdamW(self.model.parameter_groups(),lr=1e-4)
        self.model.save_checkpoint(self.champion,self.optimizer)
        self.model.save_checkpoint(self.candidate,self.optimizer)
        with torch.no_grad():
            self.model.controller.market_fusion.policy.bias[2]+=1.5
            self.model.controller.market_fusion.allocation.bias[0]+=.8
        loss=sum(p.square().sum() for g in self.model.parameter_groups() for p in g['params'])
        self.optimizer.zero_grad();loss.backward();self.optimizer.step()
        self.model.optimizer_updates=7
        self.model.config['applied_replay_rows']={'42':1};self.model.config['replay_account_episode']='candidate-only'
        save_runtime_state(self.model,self.optimizer,self.candidate)
        self.pair=snapshot_pair(self.champion,self.candidate,self.root/'evaluation')
        self.result=dict(state='qualified',evaluation_states=self.pair,scores={'paper':dict(delta=.02,
            champion=dict(net_return=.01,max_drawdown=.02),candidate=dict(net_return=.03,max_drawdown=.01))})
    def tearDown(self):self.temp.cleanup()

    def test_actual_weights_optimizer_and_rollback_are_preserved(self):
        champion_before=self.champion.read_bytes();candidate_before=self.candidate.read_bytes()
        prior=training_state(self.champion)
        receipt=promote(self.champion,self.result,self.root/'rollback')
        winner=training_state(self.champion)
        self.assertEqual(winner['optimizer_updates'],7)
        self.assertTrue(winner['optimizer']['state'])
        self.assertEqual(winner['learning_state'],{})
        self.assertEqual(winner['candidate_learning_lineage']['applied_replay_rows'],{'42':1})
        self.assertTrue(torch.equal(winner['controller']['market_fusion.policy.bias'],self.model.controller.market_fusion.policy.bias))
        restored=fixture_model(self.root);saved=load_runtime_state(restored,self.champion)
        opt=torch.optim.AdamW(restored.parameter_groups(),lr=1e-4);opt.load_state_dict(saved)
        self.assertEqual(restored.optimizer_updates,7)
        rollback(self.champion,receipt)
        rolled=training_state(self.champion)
        self.assertTrue(torch.equal(rolled['controller']['market_fusion.policy.bias'],prior['controller']['market_fusion.policy.bias']))
        self.assertEqual(rolled['optimizer_updates'],0)
        self.assertEqual(self.champion.read_bytes(),champion_before)
        self.assertEqual(self.candidate.read_bytes(),candidate_before)

    def test_pair_evaluates_distinct_learned_outputs(self):
        snapshot=dict(symbols=['AAPL'],as_of='2026-10-07',currencies={'AAPL':'USD'},current_weights={'AAPL':0},expert_inputs={})
        outputs=[]
        for role in ('champion','candidate'):
            self.model.load_assembly_state(self.pair[role]['path'])
            with torch.no_grad():result,_=self.model(snapshot,torch.zeros(1,1,16),packets=[])
            outputs.append(result['trading_output']['action_probabilities'])
        self.assertNotEqual(outputs[0],outputs[1])

    def test_state_changed_after_evaluation_cannot_be_promoted(self):
        self.model.optimizer_updates+=1
        save_runtime_state(self.model,self.optimizer,self.candidate)
        with self.assertRaisesRegex(ValueError,'changed after evaluation'):promote(self.champion,self.result,self.root/'rollback')
        self.assertFalse(trainable_path(self.champion).exists())

    def test_recipe_only_scores_cannot_publish_weights(self):
        with self.assertRaisesRegex(ValueError,'verified learned-state'):
            promote(self.champion,dict(state='qualified',scores={}),self.root/'rollback')

    def test_paired_paper_evaluation_uses_each_actual_snapshot(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        trial_spec=importlib.util.spec_from_file_location('integration_trial',ROOT/'scripts/run_assembly_trial.py')
        trial=importlib.util.module_from_spec(trial_spec);trial_spec.loader.exec_module(trial)
        from stockrl.market_panel import GlobalMarketPanel
        frame=bars(40);frame.date=pd.to_datetime(frame.date)
        market=self.root/'market.csv';frame.to_csv(market,index=False)
        panel=GlobalMarketPanel(market,raw_frame=frame)
        rows=[]
        for i in range(35,39):
            data=dict(symbols=['AAPL'],as_of=str(frame.date.iloc[i]),series=[[float(frame.close.iloc[i])]])
            packet=self.model.experts['fincast'](None,data,'cpu');packet['expert']='fincast'
            rows.append(dict(timestamp=str(frame.date.iloc[i]),decision=dict(raw_outputs=[packet])))
        args=SimpleNamespace(candidate_id='candidate',state=self.root/'trial',evaluation_market=market,
            evaluation_frame=frame,evaluation_daily=pd.DataFrame(columns=['date']),device='cpu')
        args.state.mkdir()
        states_before={role:Path(record['path']).read_bytes() for role,record in self.pair.items()}
        scores=[]
        for role in ('champion','candidate'):
            recipe=dict(candidate_id=role,refresh_seconds={'fincast':7200})
            scores.append(trial.evaluate(args,self.model,recipe,'paper',rows,None,panel,self.pair[role]['path']))
        self.assertEqual(scores[0]['decisions'],scores[1]['decisions'])
        self.assertEqual(scores[0]['initial_NAV'],scores[1]['initial_NAV'])
        self.assertEqual(scores[0]['first_as_of'],scores[1]['first_as_of'])
        self.assertGreater(scores[0]['trades'],0)
        self.assertGreater(scores[1]['net_return'],scores[0]['net_return'])
        for role,record in self.pair.items():self.assertEqual(Path(record['path']).read_bytes(),states_before[role])


if __name__=='__main__':unittest.main()
