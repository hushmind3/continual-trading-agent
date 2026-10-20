import {useState} from 'react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage,Select,Textarea} from '@platform/ui/Primitives';
import {failure,prefix,type Settings} from '../../types';
import {useAgentSettings} from '../useAgentSettings';

export function AgentPrompts({busy}:{busy:boolean}){
 const {cfg,error,setError,reload}=useAgentSettings();
 const [selected,setSelected]=useState('CEO'),[drafts,setDrafts]=useState<Record<string,string>>({});
 const [pending,setPending]=useState(false),[notice,setNotice]=useState('');
 const profile=cfg?.agent_prompt_profiles?.find(item=>item.id===selected);
 const saved=cfg?.agent_prompts?.[selected]??'';
 const text=drafts[selected]??saved;
 const edit=(value:string)=>{setDrafts(previous=>({...previous,[selected]:value}));setNotice('')};
 const save=async()=>{
  const key=selected,value=text;
  setPending(true);setError('');setNotice('');
  try{
   await request<Settings>(prefix+'settings',{agent_prompts:{[key]:value}});
   reload();
   setNotice('저장했습니다. 다음 총괄 요청과 직원 회의 발언부터 적용됩니다.');
  }catch(e){setError(failure(e))}finally{setPending(false)}
 };
 return <section className="hermes-settings">
  <p className="hermes-muted">시스템 프롬프트에 조직 공통 지침과 선택한 역할의 지침을 더합니다. 총괄의 대화와 직원의 회의 발언에 적용하며, 일반 대화와 임의 위임 작업에는 자동 적용하지 않습니다. 도구 권한과 승인 규칙은 그대로 적용됩니다.</p>
  <label>편집 대상<Select aria-label="개별 프롬프트 대상" value={selected} disabled={!cfg||pending} onChange={e=>{setSelected(e.target.value);setNotice('')}}>{cfg?.agent_prompt_profiles?.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
  <label>{profile?.name??'개별'} 지침<Textarea aria-label="개별 프롬프트 내용" rows={14} maxLength={20000} value={text} disabled={!cfg||busy||pending} onChange={e=>edit(e.target.value)}/></label>
  <div className="hermes-actions">
   <Button tone="primary" busy={pending} disabled={!cfg||busy||pending||text===saved} onClick={()=>void save()}>개별 프롬프트 저장</Button>
   <Button disabled={!profile||busy||pending||text===profile.default_prompt} onClick={()=>profile&&edit(profile.default_prompt)}>기본 지침 불러오기</Button>
   <span role="status" className="hermes-muted">{notice||(busy?'작업을 완료하거나 중지한 뒤 저장할 수 있습니다.':text!==saved?'저장하지 않은 변경이 있습니다.':'기본 지침도 수정해서 저장할 수 있습니다.')}</span>
  </div>
  <ErrorMessage message={error}/>
 </section>;
}
