import {useEffect,useState} from 'react';
import {request} from '../../../../../data/api';
import {Button,ErrorMessage,Textarea} from '../../../../../ui/Primitives';
import {failure,prefix,type Settings} from '../../types';

export function SystemPrompt({busy}:{busy:boolean}){
 const [text,setText]=useState(''),[saved,setSaved]=useState('');
 const [loaded,setLoaded]=useState(false),[pending,setPending]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 useEffect(()=>{let live=true;
  void request<Settings>(prefix+'settings',{},'GET').then(cfg=>{if(live){setText(cfg.system_prompt||'');setSaved(cfg.system_prompt||'');setLoaded(true)}}).catch(e=>{if(live)setError(failure(e))});
  return()=>{live=false};
 },[]);
 const save=async()=>{setPending(true);setError('');setNotice('');
  try{const cfg=await request<Settings>(prefix+'settings',{system_prompt:text});setText(cfg.system_prompt||'');setSaved(cfg.system_prompt||'');setNotice('저장했습니다. 다음 대화 요청부터 적용됩니다.')}
  catch(e){setError(failure(e))}finally{setPending(false)}
 };
 return <section className="hermes-settings">
  <div className="hermes-section-heading"><div><h3>시스템 프롬프트</h3><p className="hermes-muted">역할·작업 방식·응답 규칙을 추가합니다.</p></div></div>
  <label>시스템 프롬프트<Textarea aria-label="시스템 프롬프트" rows={14} value={text} disabled={!loaded||busy||pending} onChange={e=>{setText(e.target.value);setNotice('')}} placeholder="예: 한국어로 답하고, 실제 도구 결과가 확인된 경우에만 완료라고 설명하세요."/></label>
  <div className="hermes-actions"><Button tone="primary" disabled={!loaded||busy||pending||text===saved} busy={pending} onClick={()=>void save()}>시스템 프롬프트 저장</Button><span className="hermes-muted" role="status">{notice||(!loaded&&!error?'설정을 불러오는 중입니다…':busy?'작업을 중지하거나 완료한 뒤 변경할 수 있습니다.':text!==saved?'저장하지 않은 변경이 있습니다.':'')}</span></div>
  <ErrorMessage message={error}/>
 </section>;
}
