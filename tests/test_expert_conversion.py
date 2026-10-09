import unittest
from unittest.mock import patch
import torch
from torch import nn
from stockrl.platform.quantized_linear import pack_weight,PackedLinear,restore_packed,linear_layers
from stockrl.platform.batch_readiness import batch_plan
from stockrl.platform.config import LearningSettings
from stockrl.platform.model_composition import compose_policy
from stockrl.platform.policy import build_policy,parameters
from stockrl.platform.expert_inputs import admission_input
from stockrl.platform.expert_conversion import quality_check
from stockrl.platform.work_devices import choose_device
from stockrl.platform.config import Settings
from stockrl.platform.native_upgrade import match_weights
from stockrl.platform.hf_forecast import definition,HfForecastExpert
from stockrl.platform.expert_contracts import input_contract
from stockrl.platform.experience_schema import extend_observation,can_extend
from stockrl.platform.policy import observation
import numpy as np
import tempfile
from pathlib import Path
from stockrl.platform.expert_packages import split_asset,HEADER_FORMAT
from stockrl.platform.expert_optimizer import best_precision
from stockrl.platform.library_operations import LibraryOperations
from types import SimpleNamespace
from unittest.mock import Mock


class PrecisionTests(unittest.TestCase):
    def test_optimizer_deployment_uses_the_control_owner_and_restores_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);rt=SimpleNamespace(root=root,config=root/'config.json',controls={'engine':True,'paper':True,'learning':True,'feed':True},
                command=Mock(),closing=Mock(is_set=Mock(return_value=False)))
            operations=LibraryOperations(rt)
            operations.catalog_path.write_text('{"installed":{"a":"hash"}}',encoding='utf-8')
            with (patch.object(operations,'_pause') as pause,patch.object(operations,'_execute',side_effect=[{'target_active':['a_fp16'],'base':'a'},None]) as execute,
                 patch('stockrl.platform.config.load_settings',return_value=Mock()),patch('stockrl.platform.data_universe.prepare',return_value=root/'feed.json')):
                operations._run('optimize',{})
            pause.assert_called_once_with('apply')
            self.assertEqual(execute.call_args_list[-1].args[:2],('apply',{'active':['a_fp16'],'optimizer_base':'a'}))
            rt.command.assert_any_call('engine',True,internal=True)
            rt.command.assert_any_call('paper',True,internal=True)
    def test_optimizer_only_selects_measurably_better_passing_variants(self):
        def row(key,seconds,memory,passed=True):return dict(id=key,bytes=100,passed=passed,measurement={'warm_median_seconds':seconds,'metrics':{'peak_ram_bytes':memory,'peak_vram_bytes':0}})
        reports=[row('original',1,400),row('fp16',.8,200),row('int4',.1,100,False)]
        self.assertEqual(best_precision(reports,'original','balanced',1000,1000)['id'],'fp16')
        reports=[row('original',1,400),row('fp16',.98,395)]
        self.assertEqual(best_precision(reports,'original','balanced',1000,1000)['id'],'original')
        self.assertEqual(reports[1]['decision'],'not_selected')
        self.assertIn('5% 미만',reports[1]['reason'])
        reports=[row('original',1,400),row('fp16',2,200),row('int4',.1,100,False)]
        best_precision(reports,'original','balanced',1000,1000)
        self.assertTrue(reports[1]['eligible']);self.assertEqual(reports[2]['decision'],'rejected')
        reports=[row('original',1,400),row('current',.5,200,False)]
        self.assertEqual(best_precision(reports,'current','balanced',1000,1000)['id'],'original')
        self.assertIn('정확도를 우선',reports[0]['reason'])
    def test_mutable_header_is_replaceable_while_a_reader_keeps_loaded_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'champion.pt';initial={'format':HEADER_FORMAT,'state_dict':{'weight':torch.ones(4)}}
            torch.save(initial,path);reader=split_asset(path)
            temporary=path.with_suffix('.partial');torch.save({**initial,'version':1},temporary);temporary.replace(path)
            self.assertTrue(torch.equal(reader['state_dict']['weight'],torch.ones(4)))
            self.assertEqual(torch.load(path,weights_only=True)['version'],1)
    def test_added_market_slot_preserves_historical_availability(self):
        value={'expert_mask':torch.tensor([[True,False],[False,True]]),'evidence':{'a':torch.ones(2,4),'b':torch.ones(2,6)},'action':torch.ones(3)}
        expanded=extend_observation(value,['a','b'],['a','added','b'],{'a':4,'b':6,'added':5})
        self.assertTrue(torch.equal(expanded['expert_mask'],torch.tensor([[True,False,False],[False,False,True]])))
        self.assertTrue(torch.equal(expanded['action'],value['action']))
        self.assertEqual(expanded['evidence']['added'].sum(),0)
        self.assertNotIn('added',value['evidence'])
        previous={'config':{'router_family':'per-expert-context-v1','feature_sizes':{'a':4,'b':6}}}
        self.assertTrue(can_extend(previous,{'config':{'feature_sizes':{'a':4,'b':6,'added':5}}}))
        self.assertFalse(can_extend(previous,{'config':{'feature_sizes':{'a':4}}}))

    def test_added_unavailable_slot_preserves_behavior_and_value(self):
        ids=['a','b'];cfg={'feature_sizes':{'a':4,'b':6},'stock_policy_ids':[],'router_family':'per-expert-context-v1'}
        actor,critic=build_policy({'expert_ids':ids,'config':cfg});actor.eval();critic.eval()
        old=observation({'a':np.ones((2,4)),'b':np.ones((2,6))},np.ones((2,2),bool),np.ones((2,16)),np.ones((2,8)),{})
        saved={'expert_ids':ids,'actor':actor.state_dict(),'critic':critic.state_dict()}
        target={'expert_ids':['a','added','b'],'config':{**cfg,'feature_sizes':{'a':4,'b':6,'added':5}}}
        new,new_critic,_=compose_policy(saved,target,LearningSettings());new.eval();new_critic.eval()
        expanded=extend_observation(old.to_dict(),ids,target['expert_ids'],target['config']['feature_sizes'])
        from tensordict import TensorDict
        expanded=TensorDict(expanded,batch_size=[])
        with torch.no_grad():
            actor(old);critic(old);new(expanded);new_critic(expanded)
        self.assertTrue(torch.allclose(old['loc'],expanded['loc'],atol=1e-6))
        self.assertTrue(torch.allclose(old['state_value'],expanded['state_value'],atol=1e-6))
    def test_official_bolt_definition_restores_frozen_and_handles_dynamic_batch(self):
        cfg=dict(architectures=['ChronosBoltModelForForecasting'],decoder_start_token_id=0,pad_token_id=0,eos_token_id=1,d_model=16,d_ff=32,num_layers=1,num_decoder_layers=1,num_heads=2,d_kv=8,
            chronos_config=dict(context_length=32,prediction_length=16,input_patch_size=8,input_patch_stride=8,quantiles=[i/10 for i in range(1,10)]))
        kind,_=definition(cfg)
        from stockrl.platform.hf_forecast import construct
        source=construct(cfg,kind)
        package=dict(entry={'id':'test','backend':kind},metadata={'model_config':cfg},state_dict={'models.0.'+k:v for k,v in source.state_dict().items()})
        restored=HfForecastExpert.restore(package)
        self.assertTrue(input_contract(package['entry'])['supported'])
        self.assertFalse(any(p.requires_grad for p in restored.parameters()))
        for count in (1,3):
            data=dict(series=[list(range(1,33))]*count,symbols=[str(i) for i in range(count)],as_of='2026-10-09',units='price',sampling_seconds=60)
            packet=restored(None,data)
            self.assertEqual(packet['output_shape'],[count,1,9])
    def test_cuda_choice_uses_memory_budget_and_explicit_selection(self):
        settings=Settings()
        with patch('torch.cuda.is_available',return_value=True),patch('torch.cuda.mem_get_info',return_value=(4*2**30,8*2**30)),patch('stockrl.platform.resources.ResourceMonitor.snapshot',return_value={'gpu':{}}):
            self.assertEqual(choose_device(settings,'auto',1*2**30)['device'],'cuda:0')
            self.assertEqual(choose_device(settings,'auto',4*2**30)['device'],'cpu')
            self.assertEqual(choose_device(settings,'auto',conversion=True)['device'],'cuda:0')
            with self.assertRaises(MemoryError):choose_device(settings,'cuda:0',4*2**30)

    def test_native_safetensors_may_omit_proven_shared_aliases(self):
        weight=torch.ones(8,4)
        package=dict(module_count=1,state_dict={'models.0.shared.weight':weight,'models.0.encoder.weight':weight,'models.0.bias':torch.ones(8)})
        matched=match_weights({'shared.weight':torch.zeros(8,4),'bias':torch.zeros(8)},package)
        self.assertIsNotNone(matched)
        self.assertIs(matched['models.0.shared.weight'],matched['models.0.encoder.weight'])
        self.assertIsNone(match_weights({'shared.weight':torch.ones(7,4),'bias':torch.zeros(8)},package))
    def test_admission_uses_fresh_market_not_first_alphabetical_batch(self):
        batches=[{'symbols':['KR'], 'observation_timestamps':[['2026-10-08 06:00:00']],'sampling_seconds':60},
                 {'symbols':['US'], 'observation_timestamps':[['2026-10-08 14:00:00']],'sampling_seconds':60}]
        self.assertEqual(admission_input(batches,{'as_of':'2026-10-08 14:01:00'})['symbols'],['US'])
        with self.assertRaises(ValueError):admission_input(batches[:1],{'as_of':'2026-10-08 14:01:00'})
        self.assertIsNone(admission_input([None],{}))

    def test_quantization_difference_is_not_silent_admission(self):
        item={'conversion':{},'check':{'status':'passed'}}
        comparison={'relative_rmse':.34,'action_agreement':.88,'input_sha256':'same-input'}
        quality_check(item,comparison,{})
        self.assertEqual(item['check']['status'],'quality_warning')
        self.assertFalse(item['conversion']['validation']['passed'])
        quality_check(item,comparison,{'max_relative_rmse':.4,'min_action_agreement':.8})
        self.assertEqual(item['check']['status'],'passed')
        with self.assertRaises(ValueError):quality_check(item,comparison,{'max_relative_rmse':float('nan')})

    def test_packed_int4_and_int8_roundtrip_real_linear_forward(self):
        torch.manual_seed(1)
        original=nn.Linear(192,256).requires_grad_(False);x=torch.randn(3,192)
        before=original.weight.clone()
        for bits,tolerance in ((8,.015),(4,.15)):
            q,s=pack_weight(original.weight,bits);module=PackedLinear(original,bits)
            module.load_state_dict({'qweight':q,'scales':s,'bias':original.bias},assign=True)
            actual=module(x);expected=original(x)
            self.assertLess(float(torch.linalg.vector_norm(actual-expected)/torch.linalg.vector_norm(expected)),tolerance)
            self.assertLess(q.numel()*q.element_size()+s.numel()*s.element_size(),original.weight.numel()*4)
            self.assertFalse(any(p.requires_grad for p in module.parameters()))
        self.assertTrue(torch.equal(original.weight,before))

    def test_odd_width_and_zero_groups(self):
        original=nn.Linear(5,3,bias=False).requires_grad_(False);original.weight.zero_()
        q,s=pack_weight(original.weight,4);module=PackedLinear(original,4)
        module.load_state_dict({'qweight':q,'scales':s},assign=True)
        self.assertTrue(torch.equal(module(torch.ones(2,5)),torch.zeros(2,3)))

    def test_restored_packed_state_and_shared_embedding_exclusion(self):
        model=nn.Sequential(nn.Linear(65,64),nn.ReLU(),nn.Linear(64,3)).requires_grad_(False)
        state=model.state_dict();q,s=pack_weight(state.pop('0.weight'),4)
        state.update({'0.qweight':q,'0.scales':s})
        restore_packed(model,state,{'models.0.0':{'bits':4,'group_size':64}},prefix='models.0')
        self.assertTrue(torch.isfinite(model(torch.ones(1,65))).all())
        tied=nn.Module();tied.embedding=nn.Embedding(65,64);tied.linear=nn.Linear(64,65,bias=False)
        tied.linear.weight=tied.embedding.weight
        self.assertEqual(linear_layers(tied),{})

    def test_live_batch_timeout_never_trains_singletons_or_mixed_groups(self):
        settings=LearningSettings()
        replay={'batch_ready':7,'groups':[{'ready':7,'oldest_created':100}]}
        self.assertEqual(batch_plan(replay,settings,now=399)['required'],32)
        self.assertEqual(batch_plan(replay,settings,now=400)['required'],7)
        replay={'batch_ready':3,'groups':[{'ready':3,'oldest_created':0},{'ready':3,'oldest_created':0}]}
        self.assertEqual(batch_plan(replay,settings,now=10000)['required'],32)
        replay={'batch_ready':32,'groups':[{'ready':32,'oldest_created':400}]}
        self.assertEqual(batch_plan(replay,settings,now=401)['required'],32)

    def test_precision_variant_inherits_learned_slot_and_independent_adam(self):
        cfg={'feature_sizes':{'market':4},'stock_policy_ids':[],'router_family':'per-expert-context-v1'}
        actor,critic=build_policy({'expert_ids':['market'],'config':cfg})
        optimizer=torch.optim.AdamW(parameters(actor,critic),lr=.003)
        sum(p.square().sum() for p in actor.parameters()).backward();optimizer.step()
        saved={'expert_ids':['market'],'actor':actor.state_dict(),'critic':critic.state_dict(),'optimizer':optimizer.state_dict()}
        spec={'expert_ids':['market','market_int4'],'active_experts':['market_int4'],
              'config':{**cfg,'feature_sizes':{'market':4,'market_int4':4}},'slot_sources':{'market_int4':'market'}}
        result,_,opt=compose_policy(saved,spec,LearningSettings())
        source=dict(actor.named_parameters())
        for name,param in result.named_parameters():
            if 'market_int4' not in name.split('.'):continue
            original=source[name.replace('.market_int4.','.market.')]
            self.assertTrue(torch.equal(param,original),name)
            for key,value in opt.state[param].items():
                self.assertTrue(torch.equal(value,optimizer.state[original][key]))
                self.assertNotEqual(value.data_ptr(),optimizer.state[original][key].data_ptr())


if __name__=='__main__':unittest.main()
