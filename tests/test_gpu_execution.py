import unittest
import torch
from torch import nn
from stockrl.expert_device import host_state,finish_device,restore_host
from stockrl.platform.nf4_linear import pack_nf4,NF4Linear
from stockrl.platform.expert_conversion import quality_check
from stockrl.platform.experience_schema import extend_observation,can_extend


class GPUExecutionTests(unittest.TestCase):
    @unittest.skipUnless(torch.cuda.is_available(),'CUDA required')
    def test_resident_model_keeps_gpu_storage_without_a_retained_host_copy(self):
        model=nn.Linear(64,64).requires_grad_(False);model.keep_device=True;model.retain_host_weights=False
        original=model.weight.clone();home=host_state(model);model.to('cuda');finish_device(model,home,'cuda:0')
        self.assertNotIn('_device_home',model.__dict__);pointer=model.weight.data_ptr()
        for _ in range(3):
            with torch.inference_mode():model(torch.ones(1,64,device='cuda'))
            finish_device(model,host_state(model),'cuda:0')
        self.assertEqual(pointer,model.weight.data_ptr());restore_host(model)
        self.assertEqual(model.weight.device.type,'cpu');self.assertTrue(torch.equal(model.weight,original))

    @unittest.skipUnless(torch.cuda.is_available(),'CUDA required')
    def test_native_nf4_kernel_uses_compact_frozen_buffers(self):
        model=nn.Linear(128,128).requires_grad_(False);packed=pack_nf4(model.weight)
        converted=NF4Linear(model,packed).to('cuda')
        self.assertLess(sum(v.numel()*v.element_size() for v in packed.values()),model.weight.numel()*4)
        with torch.inference_mode():result=converted(torch.ones(2,128,device='cuda'))
        self.assertEqual(tuple(result.shape),(2,128));self.assertTrue(torch.isfinite(result).all())
        self.assertFalse(any(p.requires_grad for p in converted.parameters()))

    def test_functional_admission_records_reference_error_without_blocking(self):
        item={'conversion':{},'check':{'status':'passed'}}
        quality_check(item,{'relative_rmse':.1,'action_agreement':.8,'input_sha256':'fixture'},{'validation_mode':'functional'})
        self.assertTrue(item['conversion']['validation']['passed']);self.assertFalse(item['conversion']['validation']['reference_passed'])
        self.assertEqual(item['check']['status'],'passed')

    def test_new_policy_slot_is_unavailable_in_old_experience(self):
        old={'config':{'router_family':'per-expert-context-v1','feature_sizes':{'market':4,'stock':7},'stock_policy_ids':['stock']}}
        new={'config':{'feature_sizes':{'market':4,'stock':7,'stock_nf4':7},'stock_policy_ids':['stock','stock_nf4']}}
        self.assertTrue(can_extend(old,new))
        obs={'expert_mask':torch.ones(2,2,dtype=torch.bool),'evidence':{'market':torch.ones(2,4),'stock':torch.ones(2,7)},'policy_q':{'stock':torch.ones(2,4)}}
        extended=extend_observation(obs,['market','stock'],['market','stock','stock_nf4'],new['config']['feature_sizes'],new['config']['stock_policy_ids'])
        self.assertFalse(extended['expert_mask'][:,-1].any());self.assertEqual(extended['policy_q']['stock_nf4'].sum(),0)
        self.assertTrue(torch.equal(extended['policy_q']['stock'],obs['policy_q']['stock']))


if __name__=='__main__':unittest.main()
