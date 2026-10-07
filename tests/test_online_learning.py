"""TorchRL joint policy, batch learning, recovery and nonblocking inference."""
from copy import deepcopy
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
import random
import tempfile
import time
import unittest
import numpy as np
import torch
from torchrl.checkpoint import GlobalRNGState
from stockrl.experience import Experience
from stockrl.moe_policy import JointPolicy, policy_layout
from stockrl.moe_training import update_batch
from stockrl.moe_learner import AsyncLearner
from stockrl.operating_rules import operating_rules
from stockrl.moe_promotion import save_runtime_state, load_runtime_state, trainable_path
from test_integration_v1 import fixture_model


def record(model, stamp='2026-10-07T14:00'):
    snapshot = dict(symbols=['AAPL'], currencies={'AAPL':'USD'}, current_weights={'AAPL':0.},
                    as_of=stamp, tradable_symbols=['AAPL'], expert_inputs={})
    packet = dict(expert='fincast', native_output=[[100.]], symbols=['AAPL'], as_of=stamp,
                  layout='symbol,horizon', units='price', horizon=1, sampling_seconds=60)
    with torch.no_grad():decision,_=model(snapshot,torch.zeros(1,1,16),packets=[packet],explore=True)
    experience = Experience(np.zeros((2,1,17),np.float32),np.array([0]),np.array([0]),np.array([0]),
        np.ones((2,1),bool),0,2,.01,stamp,source='paper_account_portfolio',origin_model='trading_moe',
        portfolio_state=np.zeros((1,8),np.float32),account_state=np.zeros(8,np.float32),
        portfolio_reward=.01,portfolio_value_transition=True,reward_end_timestamp='2026-10-07T15:00')
    return experience,snapshot,decision


class OnlineLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        torch.manual_seed(0);torch.set_num_threads(4)
        self.model=fixture_model(self.root)
        self.optimizer=torch.optim.AdamW(self.model.parameter_groups(),lr=1e-4)
        self.rules=operating_rules()
    def tearDown(self):self.temp.cleanup()

    def test_joint_behavior_log_probability_is_exact(self):
        _,snapshot,decision=record(self.model)
        with torch.no_grad():_,output=self.model(snapshot,torch.zeros(1,1,16),packets=decision['raw_outputs'])
        b=decision['behavior'];d=JointPolicy(output['policy_logits'],output['allocation_scores'],output['cash_scores'],b['layout'])
        self.assertAlmostEqual(float(d.log_prob(torch.tensor([b['action']]))),b['log_prob'],places=6)
        out=decision['trading_output']
        self.assertAlmostEqual(sum(out['target_weights'].values())+out['cash_weights_by_currency']['USD'],1.,places=6)

    def test_batch_uses_torchrl_and_keeps_experts_frozen(self):
        records=[record(self.model,str(j)) for j in range(16)]
        old={k:p.detach().clone() for k,p in self.model.experts.named_parameters()}
        with patch('stockrl.moe_training.ClipPPOLoss',wraps=__import__('stockrl.moe_training',fromlist=['ClipPPOLoss']).ClipPPOLoss) as api:
            result=update_batch(self.model,self.optimizer,records,settings=self.rules)
        self.assertEqual(api.call_count,1)
        self.assertEqual(result['policy_contexts'],16)
        self.assertEqual(self.model.optimizer_updates,1)
        self.assertAlmostEqual(result['approximate_kl'],0.,places=5)
        for key,p in self.model.experts.named_parameters():
            self.assertTrue(torch.equal(old[key],p));self.assertFalse(p.requires_grad);self.assertIsNone(p.grad)
        self.assertTrue(any(p.grad is not None and p.grad.norm()>0 for p in self.model.adapters.parameters()))

    def test_legacy_probability_is_not_fabricated(self):
        exp,snapshot,decision=record(self.model);decision.pop('behavior')
        result=update_batch(self.model,self.optimizer,[(exp,snapshot,decision)],settings=self.rules)
        self.assertEqual(result['policy_contexts'],0)
        self.assertEqual(result['value_only_contexts'],1)

    def test_stale_or_deterministic_behavior_is_value_only(self):
        rows=[record(self.model),record(self.model)]
        rows[0][2]['behavior']['stochastic']=False
        rows[1][2]['behavior']['policy_version']=-1000
        result=update_batch(self.model,self.optimizer,rows,settings=self.rules)
        self.assertEqual(result['value_only_contexts'],2)

    def test_closed_symbols_are_fixed_and_not_in_likelihood(self):
        snapshot=dict(symbols=['AAPL','MSFT','KR'],currencies={'AAPL':'USD','MSFT':'USD','KR':'KRW'},
            tradable_symbols=['AAPL'],current_weights={'AAPL':.2,'MSFT':.3,'KR':.5})
        layout=policy_layout(snapshot,[True,True,True])
        self.assertEqual(layout['active'],[0]);self.assertEqual(layout['groups'][0]['budget'],.7)

    def test_inference_continues_while_learning_and_queue_is_bounded(self):
        learner=AsyncLearner(self.model,self.optimizer,self.rules)
        entered=Event();release=Event();original=update_batch
        def delayed(*args,**kwargs):entered.set();release.wait(3);return original(*args,**kwargs)
        records=[record(self.model)]
        try:
            with patch('stockrl.moe_learner.update_batch',side_effect=delayed):
                self.assertTrue(learner.submit(records));self.assertTrue(entered.wait(2))
                self.assertFalse(learner.submit(records))
                before=self.model.optimizer_updates
                for _ in range(8):record(self.model)
                self.assertEqual(before,self.model.optimizer_updates)
                self.assertIsNone(learner.poll(self.model,self.optimizer))
                release.set();result,credited=learner.poll(self.model,self.optimizer,wait=True)
            self.assertEqual(len(credited),1);self.assertEqual(self.model.optimizer_updates,1)
            self.assertEqual(result['policy_contexts'],1)
            self.assertFalse(hasattr(learner.model,'experts'))
        finally:release.set();learner.close()

    def test_failure_keeps_live_weights_and_can_retry(self):
        learner=AsyncLearner(self.model,self.optimizer,self.rules)
        original=deepcopy(self.model.controller.state_dict());rows=[record(self.model)]
        try:
            with patch('stockrl.moe_learner.update_batch',side_effect=RuntimeError('injected')):
                learner.submit(rows);self.assertIsNone(learner.poll(self.model,self.optimizer,wait=True))
            self.assertIn('injected',learner.error)
            for key,value in original.items():self.assertTrue(torch.equal(value,self.model.controller.state_dict()[key]))
            self.assertFalse(learner.submit(rows));learner.retry_after=0
            self.assertTrue(learner.submit(rows));self.assertIsNotNone(learner.poll(self.model,self.optimizer,wait=True))
        finally:learner.close()

    def test_low_available_ram_defers_without_mutating_weights(self):
        learner=AsyncLearner(self.model,self.optimizer,self.rules)
        try:
            with patch('stockrl.moe_learner.psutil.virtual_memory',return_value=SimpleNamespace(available=1)):
                self.assertFalse(learner.submit([record(self.model)]))
            self.assertEqual(learner.stats['deferred'],1);self.assertEqual(self.model.optimizer_updates,0)
        finally:learner.close()

    def test_rng_optimizer_and_cutoff_resume_from_small_state(self):
        update_batch(self.model,self.optimizer,[record(self.model)],settings=self.rules)
        self.model.config['training_cutoff']='2026-10-07T15:00'
        checkpoint=self.root/'fixture.pt';self.model.save_checkpoint(checkpoint)
        save_runtime_state(self.model,self.optimizer,checkpoint)
        expected=(random.random(),np.random.rand(),torch.rand(3))
        loaded=fixture_model(self.root);saved=load_runtime_state(loaded,checkpoint)
        GlobalRNGState().load_state_dict(loaded.resume_rng)
        actual=(random.random(),np.random.rand(),torch.rand(3))
        self.assertEqual(expected[:2],actual[:2]);self.assertTrue(torch.equal(expected[2],actual[2]))
        self.assertEqual(loaded.config['training_cutoff'],'2026-10-07T15:00')
        self.assertEqual(loaded.optimizer_updates,1);self.assertTrue(saved['state'])
        self.assertLess(trainable_path(checkpoint).stat().st_size,2*1024**2)

    def test_nonfinite_reward_fails_before_optimizer_update(self):
        exp,snapshot,decision=record(self.model);exp.portfolio_reward=float('nan')
        with self.assertRaisesRegex(ValueError,'nonfinite'):
            update_batch(self.model,self.optimizer,[(exp,snapshot,decision)],settings=self.rules)
        self.assertEqual(self.model.optimizer_updates,0)

    def test_resources_are_bounded_and_report_actual_process_measurements(self):
        from stockrl.gpu_scheduler import ResourceMonitor
        monitor=ResourceMonitor()
        for i in range(80):
            with monitor.measure('task:'+str(i)):pass
        result=monitor.snapshot()
        self.assertEqual(len(result['measurements']),64)
        self.assertGreater(result['rss_bytes'],0)
        self.assertGreater(result['available_ram_bytes'],0)
        self.assertGreater(result['threads'],0)

    def test_native_admission_uses_observed_vram_and_available_ram(self):
        from stockrl.gpu_scheduler import ResourceMonitor
        monitor=ResourceMonitor();monitor.measurements['expert:e']={'vram_growth_bytes':2*1024**3}
        with patch('torch.cuda.mem_get_info',return_value=(1024**3,8*1024**3)):
            self.assertEqual(monitor.native_device('e','cuda:0'),'cpu')
        with patch('stockrl.gpu_scheduler.psutil.virtual_memory',return_value=SimpleNamespace(available=1)):
            with self.assertRaises(MemoryError):monitor.native_device('e','cpu')

    def test_account_and_pending_restore_after_json_publication_failure(self):
        from stockrl.moe_paper import TradingMoEPaper
        from test_moe_paper import panel
        root=self.root/'account';bridge=TradingMoEPaper(root);market=panel()
        bridge.advance(market,0)
        original=(root/'paper_account.json').read_bytes()
        result=dict(as_of=str(market.dates[0]),trading_output=dict(actions={'AAPL':'BUY'},
            target_weights={'AAPL':.4},cash_weights_by_currency={'USD':.6}))
        with patch.object(bridge.paper_account,'save',side_effect=OSError('injected JSON failure')):
            with self.assertRaises(OSError):bridge.submit(result,market,0,paper_executable=True)
        self.assertEqual((root/'paper_account.json').read_bytes(),original)
        loaded=TradingMoEPaper(root)
        self.assertEqual(len(loaded.pending),1)
        self.assertEqual(len(loaded.paper_account.state['pending']),1)
        self.assertEqual(len(loaded.advance(market,1)),1)

    def test_future_evaluation_excludes_training_and_capture(self):
        from stockrl.moe_evaluation import future_rows,validate_evaluation
        pair={role:dict(holdout_after='2026-10-07T14:00:00Z') for role in ('champion','candidate')}
        rows=[{'timestamp':stamp} for stamp in ('2026-10-07T13:59','2026-10-07T14:00','2026-10-07T14:01')]
        self.assertEqual(future_rows(rows,pair),rows[-1:])
        scores={phase:{side:dict(first_as_of=first,last_as_of=last,decisions=2)
            for side in pair} for phase,first,last in [('replay','2026-10-07T14:01','2026-10-07T14:02'),
                                                     ('paper','2026-10-07T14:03','2026-10-07T14:04')]}
        validate_evaluation(pair,scores)
        for side in pair:scores['paper'][side]['first_as_of']='2026-10-07T14:02'
        with self.assertRaisesRegex(ValueError,'overlaps'):validate_evaluation(pair,scores)

    def test_holdout_collector_waits_for_actual_new_feed_and_survives_restart(self):
        from stockrl.moe_evaluation import collect_holdout
        from test_integration_v1 import bars
        market=self.root/'market.csv';bars().to_csv(market,index=False)
        args=SimpleNamespace(market=market,state=self.root/'evaluation',device='cpu',rules=dict(self.rules))
        args.rules.update(evaluation_min_observations=3,validation_min_market_minutes=3)
        pair={role:dict(holdout_after='2026-10-07T14:34:00Z') for role in ('champion','candidate')}
        counter=[35];progress=[]
        def append(_):
            counter[0]+=1;bars(counter[0]).iloc[-1:].to_csv(market,index=False,header=False,mode='a')
        with patch('stockrl.moe_evaluation.time.sleep',side_effect=append):
            rows,source=collect_holdout(args,self.model,pair,progress.append)
        self.assertEqual(len(rows),3);self.assertEqual(progress[-1],3)
        self.assertEqual(rows[0]['decision']['source_kind'],'live')
        self.assertIn('14:35',rows[0]['timestamp'])
        resumed,_=collect_holdout(args,self.model,pair,progress.append)
        self.assertEqual([r['timestamp'] for r in rows],[r['timestamp'] for r in resumed])

    def test_requested_worker_recovery_is_bounded_and_stop_is_respected(self):
        from stockrl.web.trading_moe import TradingMoELifecycle
        from stockrl.expert_registry import atomic_json
        worker=TradingMoELifecycle(checkpoint=self.root/'fake.pt',state=self.root/'worker')
        worker.state.mkdir()
        atomic_json(worker.record,dict(requested=True,restart_attempts=0,created=0))
        with patch.object(worker,'process',return_value=None),patch.object(worker,'start',return_value={'ok':True}) as start:
            self.assertIsNone(worker.recover());self.assertFalse(start.called)
            record=worker.read(worker.record);record['retry_at']=0;atomic_json(worker.record,record)
            self.assertEqual(worker.recover(),{'ok':True});start.assert_called_once_with(recovery=True)
            record=worker.read(worker.record);record['restart_attempts']=self.rules['runtime_restart_attempts'];atomic_json(worker.record,record)
            self.assertTrue(worker.recover()['exhausted']);self.assertFalse(worker.read(worker.record)['requested'])
            worker.stop();self.assertIsNone(worker.recover())

    def test_exchange_holidays_skip_cash_markets_without_stopping_crypto(self):
        from datetime import datetime,timezone
        from stockrl.live_feed import _market_session_open
        holiday=datetime(2026,10,9,1,tzinfo=timezone.utc) # Korean Hangul day, 10am KST
        self.assertFalse(_market_session_open({'market':'KRX'},holiday))
        self.assertTrue(_market_session_open({'market':'CRYPTO','asset_class':'crypto'},holiday))
        day=datetime(2026,12,25,15,tzinfo=timezone.utc)
        self.assertFalse(_market_session_open({'market':'US'},day))
        normal=datetime(2026,10,7,1,tzinfo=timezone.utc)
        self.assertTrue(_market_session_open({'market':'KRX'},normal))

    def test_missing_or_corrupt_account_json_restores_canonical_sqlite_account(self):
        from stockrl.moe_paper import TradingMoEPaper
        from test_moe_paper import panel
        root=self.root/'account';bridge=TradingMoEPaper(root);bridge.advance(panel(),0)
        saved=deepcopy(bridge.paper_account.state)
        path=root/'paper_account.json';path.unlink()
        self.assertEqual(TradingMoEPaper(root).paper_account.state,saved)
        path.write_text('{broken')
        self.assertEqual(TradingMoEPaper(root).paper_account.state,saved)

    def test_stable_policy_does_not_accumulate_unlearnable_new_experiences(self):
        from stockrl.moe_paper import TradingMoEPaper
        from test_moe_paper import panel
        bridge=TradingMoEPaper(self.root/'stable',collect_experience=False);market=panel()
        bridge.advance(market,0)
        result=dict(as_of=str(market.dates[0]),trading_output=dict(actions={'AAPL':'BUY'},
            target_weights={'AAPL':.4},cash_weights_by_currency={'USD':.6}))
        bridge.submit(result,market,0,paper_executable=True);bridge.advance(market,1)
        self.assertEqual(len(bridge.pending),0);self.assertEqual(bridge.replay.stats()['total'],0)
        self.assertEqual(bridge.paper_account.state['books']['USD']['trade_count'],1)

    def test_corrupt_optimizer_output_is_not_published(self):
        learner=AsyncLearner(self.model,self.optimizer,self.rules)
        try:
            actual_step=learner.optimizer.step
            def corrupt():
                actual_step()
                with torch.no_grad():next(learner.model.controller.parameters()).fill_(float('nan'))
            with patch.object(learner.optimizer,'step',side_effect=corrupt):
                learner.submit([record(self.model)])
                self.assertIsNone(learner.poll(self.model,self.optimizer,wait=True))
            self.assertIn('nonfinite weights',learner.error)
            self.assertTrue(all(torch.isfinite(p).all() for p in self.model.controller.parameters()))
            self.assertEqual(self.model.optimizer_updates,0)
        finally:learner.close()

    def test_vectorized_panel_exactly_matches_original_forward_fill(self):
        from stockrl.market_panel import GlobalMarketPanel,GLOBAL_FEATURES
        from test_integration_v1 import bars
        import pandas as pd
        frame=bars(25)
        other=bars(25).iloc[5::3].copy();other['symbol']='MSFT';other['close']*=2
        frame=pd.concat((frame,other),ignore_index=True)
        panel=GlobalMarketPanel(self.root/'market.csv',raw_frame=frame)
        features=np.zeros_like(panel.features);closes=np.full_like(panel.closes,np.nan);observed=np.zeros_like(panel.observed)
        for _,row in panel.frame.iterrows():
            i=list(panel.dates).index(row.date.to_datetime64());j=panel.symbols.index(row.symbol)
            features[i,j]=row[list(GLOBAL_FEATURES)].to_numpy(np.float32)
            closes[i,j]=row.close;observed[i,j]=True
        for j in range(len(panel.symbols)):
            for i in range(1,len(panel.dates)):
                if not observed[i,j]:features[i,j]=features[i-1,j];closes[i,j]=closes[i-1,j]
        np.testing.assert_array_equal(panel.features,features)
        np.testing.assert_array_equal(panel.closes,closes)
        np.testing.assert_array_equal(panel.observed,observed)

    def test_new_pending_captures_one_real_bar_not_unused_duplicate_history(self):
        from stockrl.market_panel import GlobalMarketPanel
        from stockrl.moe_paper import TradingMoEPaper
        from test_integration_v1 import bars
        panel=GlobalMarketPanel(self.root/'market.csv',raw_frame=bars(40));bridge=TradingMoEPaper(self.root/'account')
        bridge.advance(panel,35)
        result=dict(as_of=str(panel.dates[35]),trading_output=dict(actions={'AAPL':'BUY'},
            target_weights={'AAPL':.4},cash_weights_by_currency={'USD':.6}))
        bridge.submit(result,panel,35,paper_executable=True)
        self.assertEqual(bridge.pending[0]['features'].shape,(1,1,17))
        np.testing.assert_array_equal(bridge.pending[0]['features'][0],panel.features[35])

    def test_native_backend_does_not_override_configured_cpu_threads(self):
        from stockrl.moe_native import native_call
        source='def run_native(backend,root,data,device):\n import torch\n torch.set_num_threads(9)\n loaded_seconds=0\n return {"threads":torch.get_num_threads()}\n'
        torch.set_num_threads(2)
        try:
            result=native_call('fixture',self.root,{},runner_source=source)
            self.assertEqual(result['threads'],2)
        finally:torch.set_num_threads(4)

    def test_restart_preserves_behavior_likelihood_and_policy_learning(self):
        from stockrl.state_io import EvidenceJournal
        exp,snapshot,decision=record(self.model)
        journal=EvidenceJournal(self.root/'state');journal.save_contexts({exp.timestamp:(snapshot,decision)})
        restored=EvidenceJournal(self.root/'state').load_contexts()[exp.timestamp]
        self.assertEqual(restored[1]['behavior'],decision['behavior'])
        result=update_batch(self.model,self.optimizer,[(exp,*restored)],settings=self.rules)
        self.assertEqual(result['policy_contexts'],1);self.assertEqual(result['value_only_contexts'],0)

    @unittest.skipUnless(torch.cuda.is_available(),'CUDA unavailable')
    def test_native_rng_isolation_preserves_cuda_action_sampling(self):
        from stockrl.moe_native import native_call
        torch.cuda.manual_seed_all(19);state=torch.cuda.get_rng_state()
        expected=torch.rand(3,device='cuda:0');torch.cuda.set_rng_state(state)
        source='def run_native(backend,root,data,device):\n import torch\n torch.manual_seed(2026)\n loaded_seconds=0\n return {"sample":torch.rand(3,device=device).cpu().tolist()}\n'
        native_call('fixture',self.root,{},device='cuda:0',runner_source=source)
        self.assertTrue(torch.equal(expected,torch.rand(3,device='cuda:0')))

    def test_toto_partial_patch_padding_is_masked_not_fake_prices(self):
        import json
        from stockrl.moe_native import native_call
        from stockrl import expert_backends
        directory=self.root/'checkpoints/Toto-2.0-313m';directory.mkdir(parents=True)
        (directory/'config.json').write_text(json.dumps({'patch_size':32}))
        captured={}
        class Model(torch.nn.Module):
            def forecast(self,inputs,**kwargs):
                captured.update(inputs);captured.update(kwargs)
                return torch.zeros(9,1,2,1)
        module=SimpleNamespace(Toto2ModelConfig=lambda **kw:SimpleNamespace(**kw),Toto2Model=Model)
        series=np.arange(74).reshape(2,37).astype(float)+100
        with patch.object(expert_backends,'toto_native_module',return_value=module):
            result=native_call('toto',self.root,dict(series=series.tolist(),symbols=['A','B'],horizon=1),modules=[Model()])
        self.assertEqual(captured['target'].shape,(1,2,64));self.assertTrue(captured['has_missing_values'])
        self.assertFalse(captured['target_mask'][...,:27].any())
        self.assertTrue(captured['target_mask'][...,27:].all())
        np.testing.assert_array_equal(captured['target'][0,...,27:].numpy(),series)
        self.assertEqual(result['context_padding'],27)

    def test_symbol_universe_can_grow_and_shrink_without_rebuilding_controller(self):
        rows=[]
        for n in (1,17,5):
            symbols=[f'S{j}' for j in range(n)]
            snapshot=dict(symbols=symbols,currencies={s:'USD' for s in symbols},current_weights={s:0. for s in symbols},
                as_of=str(n),tradable_symbols=symbols,expert_inputs={})
            packet=dict(expert='fincast',native_output=[[100.+j] for j in range(n)],symbols=symbols,
                as_of=str(n),layout='symbol,horizon',units='price',horizon=1,sampling_seconds=60)
            with torch.no_grad():decision,_=self.model(snapshot,torch.zeros(1,n,16),packets=[packet],explore=True)
            weights=decision['trading_output']['target_weights']
            self.assertEqual(set(weights),set(symbols))
            self.assertAlmostEqual(sum(weights.values())+decision['trading_output']['cash_weights_by_currency']['USD'],1.,places=5)
            exp=Experience(np.zeros((1,n,17),np.float32),np.arange(n),np.zeros(n,int),np.zeros(n,int),
                np.ones((1,n),bool),0,2,.01,str(n),source='paper_account_portfolio',origin_model='trading_moe',
                portfolio_state=np.zeros((n,8),np.float32),account_state=np.zeros(8,np.float32),
                portfolio_reward=.01,portfolio_value_transition=True)
            rows.append((exp,snapshot,decision))
        result=update_batch(self.model,self.optimizer,rows,settings=self.rules)
        self.assertEqual(result['policy_contexts'],3)
