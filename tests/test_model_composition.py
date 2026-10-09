import io
from pathlib import Path
import tempfile
import unittest
import zipfile
import torch
from stockrl.platform.config import LearningSettings
from stockrl.platform.model_composition import compose_policy
from stockrl.platform.policy import parameter_names,build_policy, parameters,activate_policy
from stockrl.platform.expert_packages import split_asset,load_package,HEADER_FORMAT,PACKAGE_FORMAT
from stockrl.platform.expert_contracts import input_contract
from stockrl.platform.training_status import readiness
from stockrl.platform.native_upgrade import match_weights
from stockrl.platform.checkpoint import Checkpoints


class Composition(unittest.TestCase):
    def test_addition_keeps_every_old_weight_and_adam_moment(self):
        ids=['market_a','market_b','stock_a']
        spec={'expert_ids':ids,'config':{'feature_sizes':{k:4 for k in ids},'stock_policy_ids':['stock_a'],'central':{'hidden_size':32,'head_dim':16,'num_attention_heads':2,'num_key_value_heads':1,'intermediate_size':96}}}
        actor,critic=build_policy(spec);optimizer=torch.optim.AdamW(parameters(actor,critic),lr=.003)
        sum(p.square().sum() for p in actor.parameters()).backward();optimizer.step()
        saved={'expert_ids':ids,'model_spec':actor.model_spec,'actor':actor.state_dict(),
               'critic':critic.state_dict(),'optimizer':optimizer.state_dict(),'optimizer_names':[n for n,_ in parameter_names(actor,critic)]}
        target={'expert_ids':ids+['market_new'],'active_experts':ids,'config':{
            'feature_sizes':{k:4 for k in ids+['market_new']},'stock_policy_ids':['stock_a'],'central':{'hidden_size':32,'head_dim':16,'num_attention_heads':2,'num_key_value_heads':1,'intermediate_size':96},'router_family':'per-expert-context-v1'}}
        new,_,opt=compose_policy(saved,target,LearningSettings())
        original=dict(actor.named_parameters())
        for name,p in new.named_parameters():
            if name in original:
                self.assertTrue(torch.equal(p,original[name]),name)
                for field,value in opt.state[p].items():self.assertTrue(torch.equal(value,optimizer.state[original[name]][field]))
        self.assertEqual(opt.param_groups[0]['lr'],LearningSettings().learning_rate)
        self.assertFalse(any(p.requires_grad for n,p in new.named_parameters() if 'market_new' in n.split('.')))

    def test_inactive_slot_is_unchanged_by_learning(self):
        spec={'expert_ids':['market_a','market_b'],'config':{'feature_sizes':{'market_a':4,'market_b':4},
               'stock_policy_ids':[],'central':{'hidden_size':32,'head_dim':16,'num_attention_heads':2,'num_key_value_heads':1,'intermediate_size':96},'router_family':'per-expert-context-v1'}}
        actor,critic=build_policy(spec);optimizer=torch.optim.AdamW(parameters(actor,critic),lr=.01)
        sum(p.square().sum() for p in actor.parameters()).backward();optimizer.step()
        disabled={n:p.detach().clone() for n,p in actor.named_parameters() if 'market_b' in n.split('.')}
        activate_policy(actor,critic,['market_a']);optimizer.zero_grad(set_to_none=True)
        sum(p.square().sum() for p in actor.parameters() if p.requires_grad).backward();optimizer.step()
        for name,p in actor.named_parameters():
            if name in disabled:self.assertTrue(torch.equal(p,disabled[name]),name)
        activate_policy(actor,critic,['market_a','market_b'])
        self.assertTrue(all(p.requires_grad for p in actor.backend.actor.parameters()))
        self.assertFalse(any(p.requires_grad for p in actor.backend.critic_target.parameters()))

    def test_split_preserves_frozen_tensors_and_removes_bodies_from_header(self):
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as z:z.writestr('model.py','model')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'champion.pt';weights=torch.arange(12.).reshape(3,4)
            saved=dict(format='registered_vertical_trading_moe_v1',expert_mapping={'sample':{'backend':'chronos'}},
                config={'native_module_counts':{'sample':1},'feature_sizes':{'sample':4}},
                metadata=dict(architecture_sources=archive.getvalue(),native_runner_source='runner',construction_inputs={'sample':{}}),
                state_dict={'experts.sample.models.0.weight':weights,'adapters.sample.scale':torch.ones(4)})
            torch.save(saved,path);header=split_asset(path)
            self.assertEqual(header['format'],HEADER_FORMAT)
            self.assertFalse(any(k.startswith('experts.') for k in header['state_dict']))
            package=load_package(path,header['expert_packages']['sample'],verify=True)
            self.assertEqual(package['format'],PACKAGE_FORMAT)
            self.assertTrue(torch.equal(package['state_dict']['models.0.weight'],weights))
            before=path.read_bytes();split_asset(path);self.assertEqual(path.read_bytes(),before)

    def test_unregistered_input_is_rejected_before_composition(self):
        self.assertFalse(input_contract({'backend':'requires_external_order_feed'})['supported'])
        self.assertFalse(input_contract({'stock_policy':{'kind':'requires_llm_news'}})['supported'])
        self.assertTrue(input_contract({'backend':'chronos'})['supported'])

    def test_native_upgrade_requires_exact_complete_structure(self):
        package=dict(module_count=1,state_dict={'models.0.weight':torch.ones(3,4),'models.0.bias':torch.ones(3)})
        self.assertIsNotNone(match_weights({'model_state_dict':{'weight':torch.zeros(3,4),'bias':torch.zeros(3)}},package))
        self.assertIsNone(match_weights({'weight':torch.ones(2,4),'bias':torch.ones(2)},package))
        self.assertIsNone(match_weights({'weight':torch.ones(3,4)},package))

    def test_champion_contains_latest_learned_policy_and_optimizer(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'champion.pt'
            torch.save({'format':HEADER_FORMAT,'expert_packages':{},'state_dict':{}},path)
            spec={'expert_ids':['market_a'],'config':{'feature_sizes':{'market_a':4},'stock_policy_ids':[],'central':{'hidden_size':32,'head_dim':16,'num_attention_heads':2,'num_key_value_heads':1,'intermediate_size':96}},
                'source_format':HEADER_FORMAT,'source_model':str(path),'expert_packages':{}}
            actor,critic=build_policy(spec);optimizer=torch.optim.AdamW(parameters(actor,critic),lr=.003)
            checkpoint=Checkpoints(Path(directory)/'policies')
            checkpoint.save(actor,critic,optimizer,9,['market_a'],optimizer_steps=57,optimization_generation=4)
            saved=torch.load(path,weights_only=True)
            self.assertEqual(saved['learned_policy']['version'],9)
            self.assertEqual(saved['learned_policy']['optimizer_steps'],57)
            self.assertEqual(saved['learned_policy']['optimization_generation'],4)
            self.assertIsNotNone(saved['learned_policy']['optimizer'])

    def test_waiting_reports_cause_and_remaining_batch(self):
        controls=dict(engine=True,learning=True,paper=False,feed=True);workers={'learner':{'alive':True,'status':'waiting_batch'}}
        replay=dict(total=0,batch_ready=0,pending=0)
        self.assertEqual(readiness(controls,workers,replay,32)['code'],'paper_off')
        controls['paper']=True;replay['pending']=1
        self.assertEqual(readiness(controls,workers,replay,32)['code'],'settling')
        replay.update(total=12,batch_ready=8)
        state=readiness(controls,workers,replay,32)
        self.assertEqual(state['remaining'],24);self.assertIn('8/32',state['detail'])


if __name__=='__main__':unittest.main()
