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


if __name__=='__main__':unittest.main()
