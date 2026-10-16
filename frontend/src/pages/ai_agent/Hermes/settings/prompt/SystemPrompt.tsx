import {useEffect,useState} from 'react';
import {request} from '../../../../../data/api';
import {Button,ErrorMessage,Textarea} from '../../../../../ui/Primitives';
import {failure,prefix,type Settings} from '../../types';

export function SystemPrompt({busy}:{busy:boolean}){
 const [text,setText]=useState(''),[saved,setSaved]=useState(''),[loaded,setLoaded]=useState(false),[pending,setPending]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 useEffect(()=>{let live=true;void request<Settings>(prefix+'settings',{},'GET').then(cfg=>{if(live){setText(cfg.system_prompt||'');setSaved(cfg.system_prompt||'');setLoaded(true)}}).catch(e=>{if(live)setError(failure(e))});return()=>{live=false}},[]);
 const save=async()=>{setPending(true);setError('');setNotice('');try{const cfg=await request<Settings>(prefix+'settings',{system_prompt:text});setText(cfg.system_prompt||'');setSaved(cfg.system_prompt||'');setNotice('저장했습니다. 다음 대화 요청부터 적용됩니다.')}catch(e){setError(failure(e))}finally{setPending(false)}};
 return <section className="hermes-settings"><p className="hermes-muted">모델의 역할·말투·작업 방식·도구 사용 규칙을 작성하세요. Hermes 원본의 기본 시스템 안내 뒤에 추가됩니다. 빈 내용으로 저장하면 추가 지침을 사용하지 않습니다.</p><label htmlFor="hermes-system-prompt">시스템 프롬프트<Textarea id="hermes-system-prompt" aria-label="시스템 프롬프트" rows={14} value={text} disabled={!loaded||busy||pending} onChange={e=>{setText(e.target.value);setNotice('')}} placeholder="예: 한국어로 답하고, 작업 전에 관련 코드를 확인하세요. 실제 도구 결과가 확인된 경우에만 완료라고 설명하세요."/></label><div className="hermes-actions"><Button tone="primary" disabled={!loaded||busy||pending||text===saved} busy={pending} onClick={()=>void save()}>시스템 프롬프트 저장</Button><span className="hermes-muted" role="status">{notice||(!loaded&&!error?'설정을 불러오는 중입니다…':busy?'작업을 중지하거나 완료한 뒤 변경할 수 있습니다.':text!==saved?'저장하지 않은 변경이 있습니다.':'')}</span></div><ErrorMessage message={error}/></section>;
}
