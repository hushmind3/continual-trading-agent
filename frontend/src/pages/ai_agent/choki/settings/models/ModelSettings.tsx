import {useEffect,useRef,useState} from 'react';
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
 const localModels=useRef<{name:string;path:string;bytes:number;choice:string}[]>([]);
 useEffect(()=>{setLocale('ko')},[setLocale]);
 return <ModelPickerDialog title="사용할 모델 선택" alwaysGlobal
  loader={async options=>{
   const [result,local]=await Promise.all([
    api.getModelOptions({profile:'default',...options}),
    request<{root:string;models:{name:string;path:string;bytes:number}[]}>(prefix+'models/local',{},'GET'),
   ]);
   const root=local.root.replace(/\\/g,'/').replace(/\/+$/,'').toLowerCase();
   localModels.current=local.models.map(model=>{
    const path=model.path.replace(/\\/g,'/');
    const normalized=path.toLowerCase();
    const relative=root&&normalized.startsWith(root+'/')?path.slice(root.length+1):path;
    const location=relative.split('/').slice(0,-1).join('/')||'기본 폴더';
    return {...model,choice:`${model.name} · ${(model.bytes/1024**3).toFixed(1)} GB · ${location}`};
   });
   const providers=result.providers.filter(provider=>provider.authenticated||provider.is_current||provider.is_user_defined);
   if(local.models.length)providers.push({slug:'local-gguf',name:'내 컴퓨터',models:localModels.current.map(model=>model.choice),total_models:local.models.length,is_user_defined:true,source:'local'});
   const account=providers.find(provider=>provider.slug==='openai-codex'&&provider.authenticated);
   if(account){const catalog=await request<{models:{id:string}[]}>(prefix+'codex/models',{});const allowed=new Set(catalog.models.map(model=>model.id));const models=(account.models??[]).filter(model=>allowed.has(model));account.models=models;account.total_models=models.length;account.name='ChatGPT · Codex'}
   for(const provider of providers)if(provider.slug==='llamacpp')provider.name='내 컴퓨터';
   return {...result,providers};
  }}
  onApply={async({provider,model,confirmExpensiveModel})=>{
   if(provider==='local-gguf'){
    const selected=localModels.current.find(item=>item.choice===model);
    if(!selected)throw new Error('선택한 로컬 모델을 찾을 수 없습니다. 목록을 새로고침하세요.');
    await request(prefix+'settings',{local_model:selected.path});
    await request(prefix+'model/load',{path:selected.path});
   }else{
    const result=await api.setModelAssignment({scope:'main',task:'',provider,model,confirm_expensive_model:confirmExpensiveModel},'default');
    if(result?.confirm_required)return result;
   }
   window.dispatchEvent(new Event('hermes:model-changed'));onChanged();
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
    <div className="space-y-4"><p className="text-lg font-semibold">{settings?(settings.model||settings.local_model?.split(/[\\/]/).pop()||'모델 선택 미설정'):'모델을 불러오고 있습니다…'}</p>
    <p className="text-sm text-slate-500">일반 대화와 총괄이 공유하는 모델입니다. 설치된 GGUF와 연결된 계정·서비스를 같은 선택기에서 고릅니다.</p>
    {thinking.reasoning&&<ReasoningSelect {...thinking.reasoning} change={value=>{thinking.reasoning?.change(value);void request(prefix+'settings',{reasoning_effort:value}).catch(e=>setError(failure(e)))}}/>}
    <Button tone="primary" onClick={()=>setChoosing(true)}>모델 선택</Button>
   </div>
  </Panel>
  <Button onClick={()=>openOfficial('/env')}>계정·서비스 연결</Button>
  <details><summary className="cursor-pointer text-sm text-slate-500">고급 모델 설정</summary><div className="mt-3"><Button onClick={()=>openOfficial('/models')}>보조 모델·여러 모델 협업 설정</Button></div></details>
  {choosing&&<ModelChooser onClose={()=>setChoosing(false)} onChanged={refresh}/>}
 </div>;
}
