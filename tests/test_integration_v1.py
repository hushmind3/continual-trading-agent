"""Focused integration checks; synthetic fixtures never enter operational storage."""
import importlib.util
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


if __name__=='__main__':unittest.main()
