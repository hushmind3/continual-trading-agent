"""Integrated body membership, GPU evidence/SAC and shared input regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import torch
import threading
import time
from types import SimpleNamespace
from stockrl.platform.integrated_asset import integrate,read_header
from stockrl.platform.expert_packages import PACKAGE_FORMAT,digest
from stockrl.platform.observations import prepare_evidence
from stockrl.platform.tensor_evidence import prepare_tensor_evidence
from stockrl.platform.moe_session import MoESession,optimizer_to
from stockrl.platform.policy import build_policy,parameters,decide,INPUT_KEYS
from stockrl.platform.learner import register,ingest,training_state
from stockrl.platform.config import LearningSettings
from stockrl.platform.checkpoint import Checkpoints
from stockrl.moe_native import native_call
from test_platform import spec,obs


class UnifiedMoETests(unittest.TestCase):
    def test_gguf_generation_can_be_cancelled_without_waiting_for_http_timeout(self):
        from stockrl.platform.gguf_expert import GGUFExpert
        expert=GGUFExpert.__new__(GGUFExpert);torch.nn.Module.__init__(expert)
        expert.settings=SimpleNamespace(resources=SimpleNamespace(inference_timeout_seconds=180));expert.url='http://unused'
        closed=threading.Event();expert.cancelled=lambda:True;expert.close=closed.set
        def blocked(*args,**kwargs):
            if not closed.wait(3):raise AssertionError('generation was not cancelled')
            raise ConnectionError('native child stopped')
        with patch('stockrl.platform.gguf_expert.requests.post',side_effect=blocked):
            started=time.monotonic()
            with self.assertRaises(InterruptedError):expert.query({})
            self.assertLess(time.monotonic()-started,1)
        self.assertTrue(closed.is_set())

    def test_integrated_body_removal_changes_actual_file_and_restores_same_frozen_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);champion=root/'champion.pt';refs={}
            for key,count in [('small',16),('large',16384)]:
                path=root/(key+'.pt')
                torch.save(dict(format=PACKAGE_FORMAT,id=key,entry={'parameters':count},state_dict={'models.0.weight':torch.arange(count)},metadata={}),path)
                refs[key]={'file':path.name,'bytes':path.stat().st_size,'sha256':digest(path)}
            header={'expert_packages':refs,'state_dict':{'central':torch.ones(4)},'learned_policy':{'optimizer_steps':330}}
            torch.save(integrate(dict(header),champion,['small','large']),champion);large_bytes=champion.stat().st_size
            merged=torch.load(champion,weights_only=True,mmap=True)
            torch.testing.assert_close(merged['frozen_experts']['large']['state_dict']['models.0.weight'],torch.arange(16384))
            self.assertEqual(merged['integrated_summary']['frozen_parameters'],16400);del merged
            head=read_header(champion)
            self.assertNotIn('frozen_experts',head)
            torch.save(integrate(head,champion,['small']),champion)
            self.assertLess(champion.stat().st_size,large_bytes)
            only=torch.load(champion,weights_only=True)
            self.assertEqual(list(only['frozen_experts']),['small']);self.assertEqual(only['learned_policy']['optimizer_steps'],330)

    def test_tensor_evidence_matches_original_contract_and_rejects_future_and_stale_symbols(self):
        packets={'chronos':[dict(as_of='2026-10-09 00:01:00',symbols=['A','B'],native_output=[[.1],[.2]],
            symbol_as_of={'A':'2026-10-09 00:01:00','B':'2026-10-08'},horizon=1,sampling_seconds=60,layout='symbol,horizon')]}
        a,m,q=prepare_evidence(packets,['A','B'],spec(),'2026-10-09 00:01:00')
        for device in ['cpu']+(['cuda:0'] if torch.cuda.is_available() else []):
            b,n,r=prepare_tensor_evidence(packets,['A','B'],spec(),'2026-10-09 00:01:00',300,device)
            for key in a:torch.testing.assert_close(b[key].cpu(),torch.tensor(a[key]))
            self.assertTrue(torch.equal(n.cpu(),torch.tensor(m)));self.assertFalse(n[1].any())
            _,future,_=prepare_tensor_evidence(packets,['A'],spec(),'2026-10-08',300,device)
            self.assertFalse(future.any())

    def test_native_tensor_output_keeps_device_and_does_not_reset_policy_rng(self):
        source='''def run_native(expert,root,data,device):
    import torch
    import numpy as np
    torch.manual_seed(0)
    series=np.asarray([[1.,2.]])
    mean=series.mean(axis=1,keepdims=True)
    scale=series.std(axis=1,keepdims=True)
    def infer():
        normalized=torch.tensor((series-mean)/scale,device=device)
        return normalized.float().cpu().numpy()*scale+mean
    output=np.asarray(infer())
    if not np.isfinite(output).all():raise ValueError('invalid')
    return {'native_output':output.tolist()}
'''
        torch.manual_seed(23);before=torch.get_rng_state().clone()
        device='cuda:0' if torch.cuda.is_available() else 'cpu'
        result=native_call('test',Path('.'),{'_tensor_output':True},device,modules=[],runner_source=source)
        self.assertTrue(torch.is_tensor(result['native_output']));self.assertEqual(str(result['native_output'].device),device)
        torch.testing.assert_close(result['native_output'].cpu(),torch.tensor([[1.,2.]],dtype=torch.float64))
        self.assertTrue(torch.equal(before,torch.get_rng_state()))
        self.assertIsInstance(native_call('test',Path('.'),{},device,modules=[],runner_source=source)['native_output'],list)

    def test_shared_market_view_is_built_only_when_feed_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'live').mkdir();file=root/'live'/'market.csv'
            pd.DataFrame([dict(date='2026-10-09',symbol='A',close=10,market='us',asset_class='stock')]).to_csv(file,index=False)
            settings=type('Config',(),{'state_dir':root})()
            session=MoESession(settings)
            first,frame,_=session.market(view=True)
            for _ in range(10):
                view,current,_=session.market(view=True)
                self.assertIs(first,view);self.assertIs(frame,current)
            self.assertEqual(session.market_builds,1);self.assertEqual(session.view_builds,1)
            session.put_evidence('a',[{'native_output':torch.ones(2)}]);session.put_evidence('b',[])
            self.assertEqual(list(session.evidence(['a'])),['a'])

    @unittest.skipUnless(torch.cuda.is_available(),'CUDA required')
    def test_official_sac_updates_on_cuda_and_resumes(self):
        from stockrl.platform.policy import asset_observations
        torch.set_num_threads(2)
        actor,critic=build_policy(spec());actor.to('cuda');critic.to('cuda')
        engine=register(actor,LearningSettings(buffer_size=256),'cuda')
        before=next(actor.backend.actor.parameters()).detach().clone()
        for _ in range(8):
            _,td=decide(actor,critic,obs(),explore=True)
            inputs=asset_observations(td,actor.model_spec)
            for i in range(2):
                row={k:v[i].numpy()[None] for k,v in inputs.items()}
                engine.replay_buffer.add(row,row,td['action'][i].numpy()[None],np.array([.01]),np.array([0]),[{}])
        engine.train(1,4)
        self.assertFalse(torch.equal(before,next(actor.backend.actor.parameters())))
        self.assertEqual(engine._n_updates,1)
        with tempfile.TemporaryDirectory() as directory:
            cps=Checkpoints(Path(directory));cps.save(actor,critic,None,2,spec()['expert_ids'],optimizer_steps=331)
            saved,_=cps.load();self.assertEqual(saved['sac']['updates'],1)
            a,c=build_policy(saved['model_spec']);a.load_state_dict(saved['actor']);c.load_state_dict(saved['critic']);a.to('cuda')
            resumed=register(a,LearningSettings(buffer_size=256),'cuda',saved['sac'])
            self.assertEqual(resumed._n_updates,1)
            file=Path(directory)/'replay.pkl';engine.save_replay_buffer(file);resumed.load_replay_buffer(file)
            self.assertEqual(resumed.replay_buffer.size(),16)
            resumed.train(1,4);self.assertEqual(resumed._n_updates,2)
