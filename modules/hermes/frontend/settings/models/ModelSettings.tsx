import {useEffect,useState} from 'react';
import {api} from '@hermes-official/lib/api';
import {ModelPickerDialog} from '@hermes-official/components/ModelPickerDialog';
import {I18nProvider,useI18n} from '@hermes-official/i18n';
import {MemoryRouter} from '@hermes-official/platform-router';
import {Button,ErrorMessage} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {request} from '@platform/data/api';
import {prefix,failure,type Settings} from '../../types';
import {useThinking} from '../../chat/useThinking';
import {ReasoningSelect} from './ReasoningSelect';
import {openOfficial} from '../../agent_navigation';
import '../official/transport';

function Picker({onClose,onChanged}:{onClose:()=>void;onChanged:()=>void}){
 const {setLocale}=useI18n();
 useEffect(()=>{setLocale('ko')},[setLocale]);
 return <ModelPickerDialog title="사용할 모델 선택" alwaysGlobal
  loader={async options=>{
   const result=await api.getModelOptions({profile:'default',...options});
   const providers=result.providers.filter(provider=>provider.authenticated||provider.is_current||provider.is_user_defined);
   const account=providers.find(provider=>provider.slug==='openai-codex'&&provider.authenticated);
   if(account){const catalog=await request<{models:{id:string}[]}>(prefix+'codex/models',{});const allowed=new Set(catalog.models.map(model=>model.id));const models=(account.models??[]).filter(model=>allowed.has(model));account.models=models;account.total_models=models.length;account.name='ChatGPT · Codex'}
   for(const provider of providers)if(provider.slug==='llamacpp')provider.name='내 컴퓨터';
   return {...result,providers};
  }}
  onApply={async({provider,model,confirmExpensiveModel})=>{
   const result=await api.setModelAssignment({scope:'main',task:'',provider,model,confirm_expensive_model:confirmExpensiveModel},'default');
   if(!result.confirm_required){window.dispatchEvent(new Event('hermes:model-changed'));onChanged()}
   return result;
  }} onClose={onClose}/>;
}

export function ModelChooser(props:{onClose:()=>void;onChanged:()=>void}){
 return <div className="hermes-official"><MemoryRouter><I18nProvider><Picker {...props}/></I18nProvider></MemoryRouter></div>;
}

export function ModelSettings(){
 const [settings,setSettings]=useState<Settings>(),[error,setError]=useState(''),[choosing,setChoosing]=useState(false);
 const refresh=()=>{void request<Settings>(prefix+'settings',{},'GET').then(value=>{setSettings(value);setError('')}).catch(e=>setError(failure(e)))};
 const thinking=useThinking(settings?.model||'');
 useEffect(()=>{refresh();window.addEventListener('hermes:model-changed',refresh);return()=>window.removeEventListener('hermes:model-changed',refresh)},[]);
 return <div className="space-y-5">
  {error&&<ErrorMessage message={error}/>}
  <Panel title="사용할 모델">
   <div className="space-y-4"><p className="text-lg font-semibold">{settings?.model||'모델을 불러오고 있습니다…'}</p>
    <p className="text-sm text-slate-500">일반 대화와 총괄이 공유하는 모델입니다. 로컬 모델과 연결된 계정·서비스를 같은 선택기에서 고릅니다.</p>
    {thinking.reasoning&&<ReasoningSelect {...thinking.reasoning} change={value=>{thinking.reasoning?.change(value);void request(prefix+'settings',{reasoning_effort:value}).catch(e=>setError(failure(e)))}}/>}
    <Button tone="primary" onClick={()=>setChoosing(true)}>모델 선택</Button>
   </div>
  </Panel>
  <Button onClick={()=>openOfficial('/env')}>계정·서비스 연결</Button>
  <details><summary className="cursor-pointer text-sm text-slate-500">고급 모델 설정</summary><div className="mt-3"><Button onClick={()=>openOfficial('/models')}>보조 모델·여러 모델 협업 설정</Button></div></details>
  {choosing&&<ModelChooser onClose={()=>setChoosing(false)} onChanged={refresh}/>}
 </div>;
}
