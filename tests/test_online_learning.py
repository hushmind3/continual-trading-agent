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
