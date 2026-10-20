import {useState} from 'react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage,Textarea} from '@platform/ui/Primitives';
import {failure,prefix,type Settings} from '../../types';
import {useAgentSettings} from '../useAgentSettings';

export function AgentPrompts({busy}:{busy:boolean}){
 const {cfg,error,setError,acceptCfg}=useAgentSettings();
 const [drafts,setDrafts]=useState<Record<string,string>>({});
 const [pending,setPending]=useState(false),[notice,setNotice]=useState('');
 const changes=Object.fromEntries(Object.entries(drafts).filter(([key,value])=>value!==(cfg?.agent_prompts?.[key]??'')));
 const dirty=Object.keys(changes).length>0;
 const edit=(key:string,value:string)=>{setDrafts(previous=>({...previous,[key]:value}));setNotice('')};
 const save=async()=>{
  setPending(true);setError('');setNotice('');
  try{
   const saved=await request<Settings>(prefix+'settings',{agent_prompts:changes});
   acceptCfg(saved);setDrafts({});
   setNotice('저장했습니다. 다음 총괄 요청과 직원 회의 발언부터 적용됩니다.');
  }catch(e){setError(failure(e))}finally{setPending(false)}
 };
 return <section className="hermes-settings">
  <p className="hermes-muted">총괄과 직원별 지침을 함께 편집합니다. 총괄 대화와 직원 회의 발언에 적용하며, 일반 대화와 임의 위임 작업에는 자동 적용하지 않습니다. 도구 권한과 승인 규칙은 그대로 적용됩니다.</p>
  <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">{cfg?.agent_prompt_profiles?.map(profile=>{
   const text=drafts[profile.id]??cfg.agent_prompts?.[profile.id]??'';
   return <div key={profile.id} className={profile.id==='common'?'xl:col-span-2 space-y-3':'space-y-3'}>
    <label>{profile.name}<Textarea aria-label={profile.name+' 프롬프트'} rows={profile.id==='common'?3:6} maxLength={20000} value={text} disabled={busy||pending} onChange={e=>edit(profile.id,e.target.value)}/></label>
    <Button variant="ghost" disabled={busy||pending||text===profile.default_prompt} onClick={()=>edit(profile.id,profile.default_prompt)}>{profile.name} 기본 지침 불러오기</Button>
   </div>;
  })}</div>
  <div className="hermes-actions">
   <Button tone="primary" busy={pending} disabled={!cfg||busy||pending||!dirty} onClick={()=>void save()}>변경한 지침 모두 저장</Button>
   <span role="status" className="hermes-muted">{notice||(!cfg?'설정을 불러오는 중입니다…':busy?'작업을 완료하거나 중지한 뒤 저장할 수 있습니다.':dirty?'저장하지 않은 변경이 있습니다.':'기본 지침도 수정해서 저장할 수 있습니다.')}</span>
  </div>
  <ErrorMessage message={error}/>
 </section>;
}
