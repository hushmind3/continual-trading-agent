import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Select,ErrorMessage,Status} from '@platform/ui/Primitives';
import {prefix,failure} from '../../types';
import {ReasoningSelect,type CodexModel} from './ReasoningSelect';

interface Connection {state:string;connected:boolean;url?:string;code?:string;error?:string}
export function CodexModelForm({disabled,selected,selectedEffort='auto',onSelect}:{disabled:boolean;selected:string;selectedEffort?:string;onSelect:(model:string,effort:string)=>Promise<void>}) {
 const [connection,setConnection]=useState<Connection>(),[models,setModels]=useState<CodexModel[]>([]),[model,setModel]=useState(selected),[effort,setEffort]=useState(selectedEffort),[pending,setPending]=useState(''),[error,setError]=useState('');
 const refresh=async()=>{const state=await request<Connection>(prefix+'codex/status',{},'GET');setConnection(state);return state};
 const run=async(name:string,action:()=>Promise<void>)=>{setPending(name);setError('');try{await action()}catch(error){setError(failure(error))}finally{setPending('')}};
 const list=()=>run('models',async()=>{const response=await request<{models:CodexModel[]}>(prefix+'codex/models',{});setModels(response.models);setModel(value=>response.models.some(row=>row.id===value)?value:response.models[0]?.id||'')});
 useEffect(()=>{void refresh().catch(error=>setError(failure(error)))},[]);
 useEffect(()=>{if(connection?.state!=='pending')return;const timer=window.setInterval(()=>void refresh().catch(error=>setError(failure(error))),2500);return()=>window.clearInterval(timer)},[connection?.state]);
 useEffect(()=>{if(connection?.connected)void list()},[connection?.connected]);
 const chosen=models.find(row=>row.id===model);
 return <div className="ui-settings-fields">
  <p className="ui-field-hint">ChatGPT 계정으로 로그인하고 사용할 모델과 추론 수준을 선택합니다. 대화·기억·도구와 총괄 기능은 Hermes를 사용합니다.</p>
  <Status tone={connection?.connected?'good':'idle'}>{connection?.connected?'ChatGPT 연결됨':connection?.state==='pending'?'로그인 대기 중':'로그인 필요'}</Status>
  <div className="ui-settings-actions"><Button disabled={disabled||!!pending||connection?.state==='pending'} busy={pending==='login'} onClick={()=>void run('login',async()=>setConnection(await request<Connection>(prefix+'codex/login',{})))}>ChatGPT로 로그인</Button><Button disabled={disabled||!!pending||!connection?.connected} busy={pending==='models'} onClick={()=>void list()}>모델 목록 새로고침</Button></div>
  {connection?.state==='pending'&&<div className="ui-settings-notice" role="status"><p>브라우저에서 로그인한 뒤 다음 코드를 입력하세요. 약 15분 동안 유효합니다.</p><p><strong>{connection.code}</strong></p><a href={connection.url} target="_blank" rel="noreferrer">ChatGPT 로그인 화면 열기 ↗</a></div>}
  <div className="ui-settings-choice-grid"><label>사용할 모델<Select aria-label="사용할 모델" value={model} disabled={disabled||!!pending||!models.length} onChange={event=>{setModel(event.target.value);setEffort('auto')}}>{!models.length&&<option value="">로그인 후 계정 목록을 불러옵니다</option>}{models.map(row=><option key={row.id} value={row.id}>{row.name}</option>)}</Select></label><div className="ui-settings-fields"><ReasoningSelect model={chosen} value={effort} change={setEffort} disabled={disabled||!!pending}/></div></div>
  {!!models.length&&<p className="ui-field-hint">계정에서 조회한 모델 {models.length}개 · 실제 사용 가능 여부는 첫 응답 완료로 확인합니다.</p>}
  <Button tone="primary" disabled={disabled||!!pending||!connection?.connected||!chosen} busy={pending==='select'} onClick={()=>void run('select',()=>onSelect(model,effort))}>이 모델과 추론 수준 사용</Button>
  <ErrorMessage message={error||connection?.error||''}/>
 </div>;
}
