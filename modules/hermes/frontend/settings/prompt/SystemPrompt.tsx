import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage,Textarea} from '@platform/ui/Primitives';
import {failure,prefix,type Settings} from '../../types';

export function SystemPrompt({busy}:{busy:boolean}){
 const [text,setText]=useState(''),[saved,setSaved]=useState('');
 const [defaultText,setDefaultText]=useState(''),[source,setSource]=useState('default');
 const [loaded,setLoaded]=useState(false),[pending,setPending]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 useEffect(()=>{let live=true;
  void request<Settings>(prefix+'settings',{},'GET').then(cfg=>{if(live){setText(cfg.system_prompt||'');setSaved(cfg.system_prompt||'');setDefaultText(cfg.default_system_prompt||'');setSource(cfg.system_prompt_source||'default');setLoaded(true)}}).catch(e=>{if(live)setError(failure(e))});
  return()=>{live=false};
 },[]);
 const save=async()=>{setPending(true);setError('');setNotice('');
  try{const cfg=await request<Settings>(prefix+'settings',{system_prompt:text});setText(cfg.system_prompt||'');setSaved(cfg.system_prompt||'');setSource(cfg.system_prompt_source||'default');setNotice('저장했습니다. 다음 대화 요청부터 적용됩니다.')}
  catch(e){setError(failure(e))}finally{setPending(false)}
 };
 return <section className="hermes-settings">
  <div className="hermes-section-heading"><div><h3>시스템 프롬프트</h3><p className="hermes-muted">{source==='custom'?'기본 공통 지침에 기존 사용자 설정을 추가해 사용합니다.':'기본 지침을 사용 중입니다.'} 원본 Hermes의 필수 도구·승인 지침은 유지됩니다.</p></div><Button disabled={!loaded||busy||pending||text===defaultText} onClick={()=>{setText(defaultText);setNotice('기본 지침을 불러왔습니다. 저장하면 적용됩니다.')}}>기본 지침 불러오기</Button></div>
  <label>시스템 프롬프트<Textarea aria-label="시스템 프롬프트" rows={14} value={text} disabled={!loaded||busy||pending} onChange={e=>{setText(e.target.value);setNotice('')}} placeholder="예: 한국어로 답하고, 실제 도구 결과가 확인된 경우에만 완료라고 설명하세요."/></label>
  <div className="hermes-actions"><Button tone="primary" disabled={!loaded||busy||pending||text===saved} busy={pending} onClick={()=>void save()}>시스템 프롬프트 저장</Button><span className="hermes-muted" role="status">{notice||(!loaded&&!error?'설정을 불러오는 중입니다…':busy?'작업을 중지하거나 완료한 뒤 변경할 수 있습니다.':text!==saved?'저장하지 않은 변경이 있습니다.':'')}</span></div>
  <ErrorMessage message={error}/>
 </section>;
}
