import json
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
from stockrl.trading.operation_control import operations_runtime as operations
from stockrl.finrl.policy_learning import handlers as learning
from stockrl.state_io import read_json


class ContinuousLearningTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.object(operations, 'ROOT', self.root))
        self.runtime = operations.OperationsRuntime()
        self.runtime.controls['learning'] = True
        self.identity = dict(currency='USD', algorithm='sac', symbols=['AAPL'],
                             environment='PortfolioOptimizationEnv', champion_experts=[])
        self.source = 'policies/source/sac.zip'
        self.write_policy('policies/source', self.identity)
        self.selection = self.root / 'runtime/operations/policies.json'
        self.selection.parent.mkdir(parents=True)
        self.selection.write_text(json.dumps({'USD': self.source, 'KRW': 'unchanged.zip'}))
        self.frame = pd.DataFrame([dict(date=pd.Timestamp('2026-01-01'), tic='AAPL', close=100)])
        self.prices = self.stack.enter_context(patch.object(operations, 'prices', return_value=self.frame))
        self.job = {'running': False}
        self.stack.enter_context(patch.object(operations.system, 'job_state', side_effect=lambda: dict(self.job)))
        self.requests = []
        def launch(command, request, **kwargs):
            self.requests.append((request, kwargs))
            self.job = dict(id=f'{len(self.requests):032x}', output=f'policies/result{len(self.requests)}',
                            status='running', running=True)
            return {'job': dict(self.job)}
        self.stack.enter_context(patch.object(learning, 'launch', side_effect=launch))
        self.stack.enter_context(patch.object(learning, 'source_settings', return_value={}))
        self.check = self.stack.enter_context(patch.object(learning, 'model_state',
            return_value=dict(compatible=True, reasons=[], num_timesteps=200, updates=12)))
        # Checkpoint naming is exercised without importing model libraries or reading weights.
        self.stack.enter_context(patch.object(operations, 'policy_checkpoint', side_effect=lambda folder: folder/'sac.zip'))

    def write_policy(self, folder, identity):
        path = self.root/'runtime/official'/folder
        path.mkdir(parents=True, exist_ok=True)
        (path/'sac.zip').write_bytes(b'checkpoint fixture')
        (path/'dataset.json').write_text(json.dumps(identity))
        return path

    def succeed(self, identity=None):
        self.write_policy(self.job['output'], identity or self.identity)
        self.job.update(status='succeeded', running=False, exit_code=0, finished_at='2026-01-02')

    def test_running_job_is_pinned_and_does_not_mark_input_complete(self):
        self.runtime.queue_learning(['AAPL'])
        self.runtime.queue_learning(['AAPL'])
        self.assertEqual(len(self.requests), 1)
        request, flags = self.requests[0]
        self.assertTrue(request.resume)
        self.assertEqual(Path(request.checkpoint), self.root/'runtime/official'/self.source)
        self.assertTrue(flags['continuous'])
        self.assertEqual(self.runtime.learning_versions, {})

    def test_failed_job_can_retry_same_input(self):
        self.runtime.queue_learning(['AAPL'])
        self.job.update(status='failed', running=False, exit_code=1, error='worker failed')
        self.runtime.finish_learning()
        self.assertEqual(self.runtime.learning_versions, {})
        self.assertEqual(self.runtime.status['learning_error'], 'worker failed')
        self.runtime.queue_learning(['AAPL'])
        self.assertEqual(len(self.requests), 2)

    def test_success_applies_once_and_changed_data_resumes_new_checkpoint(self):
        self.runtime.queue_learning(['AAPL'])
        self.succeed()
        self.runtime.queue_learning(['AAPL'])
        self.assertEqual(len(self.requests), 1)
        selected = read_json(self.selection)
        self.assertEqual(selected['USD'], 'policies/result1/sac.zip')
        self.assertEqual(selected['KRW'], 'unchanged.zip')
        self.prices.return_value = self.frame.assign(close=101)
        self.runtime.queue_learning(['AAPL'])
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(Path(self.requests[-1][0].checkpoint), self.root/'runtime/official/policies/result1/sac.zip')

    def test_user_selection_changed_during_training_is_preserved(self):
        self.runtime.queue_learning(['AAPL'])
        self.selection.write_text(json.dumps({'USD': 'policies/other/sac.zip'}))
        self.succeed()
        self.runtime.finish_learning()
        self.assertEqual(read_json(self.selection)['USD'], 'policies/other/sac.zip')
        self.assertNotIn('learning_applied', self.runtime.status)

    def test_incompatible_output_does_not_apply_or_mark_completed(self):
        self.runtime.queue_learning(['AAPL'])
        self.succeed({**self.identity, 'symbols': ['MSFT']})
        self.runtime.finish_learning()
        self.assertEqual(read_json(self.selection)['USD'], self.source)
        self.assertEqual(self.runtime.learning_versions, {})
        self.assertIn('symbols', self.runtime.status['learning_error'])

    def test_stopped_learning_keeps_current_policy(self):
        self.runtime.queue_learning(['AAPL'])
        self.succeed()
        self.runtime.controls['learning'] = False
        self.runtime.finish_learning()
        self.assertEqual(read_json(self.selection)['USD'], self.source)
        self.assertNotIn('learning_applied', self.runtime.status)

    def test_terminal_sidecar_survives_another_global_job(self):
        self.runtime.queue_learning(['AAPL'])
        self.succeed()
        record = self.root/'runtime/official/jobs'/(self.job['id']+'.json')
        record.parent.mkdir()
        record.write_text(json.dumps(self.job))
        self.job = {'id': 'other', 'running': True, 'status': 'running'}
        self.runtime.finish_learning()
        self.assertEqual(read_json(self.selection)['USD'], 'policies/result1/sac.zip')

    def test_price_query_does_not_hold_runtime_quote_lock(self):
        started, release = threading.Event(), threading.Event()
        def slow(*args):
            started.set()
            if not release.wait(3): raise TimeoutError('query timed out')
            return self.frame
        self.prices.side_effect = slow
        worker = threading.Thread(target=self.runtime.queue_learning, args=(['AAPL'],))
        worker.start()
        try:
            self.assertTrue(started.wait(1))
            acquired = self.runtime.lock.acquire(timeout=.2)
            self.assertTrue(acquired)
            if acquired: self.runtime.lock.release()
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())


class ResumeCounterTests(unittest.TestCase):
    def test_resume_uses_pinned_weights_and_preserves_step_counter(self):
        from stockrl.finrl import framework
        from stockrl.platform import sac_champion
        from finrl.agents.stablebaselines3 import models
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            stack.enter_context(patch.object(framework, 'ROOT', root))
            stack.enter_context(patch.object(framework, 'sac_example', return_value=({}, {}, 7)))
            env = SimpleNamespace(currency='USD', symbols=['AAPL'],
                unwrapped=SimpleNamespace(observation_space=SimpleNamespace(shape=(6,))), close=MagicMock())
            stack.enter_context(patch.object(framework, 'training_environment', return_value=env))
            stack.enter_context(patch.object(sac_champion, '_candidate_identity', return_value={}))
            stack.enter_context(patch.object(sac_champion, '_policy_kwargs', return_value={}))
            stack.enter_context(patch.object(sac_champion, '_original_report', return_value={}))
            model = MagicMock(num_timesteps=100, _n_updates=1)
            model.save.side_effect = lambda path: Path(str(path)+'.zip').write_bytes(b'fixture')
            model.save_replay_buffer.side_effect = lambda path: Path(path).write_bytes(b'fixture')
            def learn(**kwargs):
                if kwargs['reset_num_timesteps']: model.num_timesteps = 0
                model.num_timesteps += kwargs['total_timesteps']
                return model
            model.learn.side_effect = learn
            agent = stack.enter_context(patch.object(models, 'DRLAgent')).return_value
            agent.get_model.return_value = model
            agent.train_model.return_value = model
            loader = stack.enter_context(patch.object(operations.system, 'model', return_value=model))
            registry = SimpleNamespace(catalog=lambda: {'active': [], 'experts': {}})
            frame = pd.DataFrame([dict(symbol='AAPL', date=pd.Timestamp('2026-01-01'), close=100)])
            original = root/'runtime/official/policies/source'
            framework.train(frame, registry, output=original)
            output = root/'runtime/official/policies/resumed'
            framework.train(frame, registry, resume=True, output=output,
                            source_checkpoint=original/'sac.zip', total_timesteps=7)
            self.assertEqual(loader.call_args.args[0], original/'sac.zip')
            self.assertFalse(model.learn.call_args.kwargs['reset_num_timesteps'])
            self.assertEqual(model.num_timesteps, 107)
            self.assertEqual(agent.train_model.call_count, 1)
            self.assertTrue(read_json(output/'dataset.json')['training_input']['fingerprint'])
            self.assertEqual(env.close.call_count, 2)
