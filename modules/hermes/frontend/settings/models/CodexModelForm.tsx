import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Input,ErrorMessage,Status} from '@platform/ui/Primitives';
import {prefix,failure} from '../../types';

interface Connection {state:string;connected:boolean;url?:string;code?:string;error?:string}
export function CodexModelForm({disabled,selected,onSelect}:{disabled:boolean;selected:string;onSelect:(model:string)=>Promise<void>}) {
 const [connection,setConnection]=useState<Connection>(),[models,setModels]=useState<string[]>([]),[model,setModel]=useState(selected),[pending,setPending]=useState(''),[error,setError]=useState(''),[live,setLive]=useState(false);
 const refresh=async()=>{const state=await request<Connection>(prefix+'codex/status',{},'GET');setConnection(state);return state};
 useEffect(()=>{void refresh().catch(error=>setError(failure(error)))},[]);
 useEffect(()=>{if(connection?.state!=='pending')return;const timer=window.setInterval(()=>void refresh().catch(error=>setError(failure(error))),2500);return()=>window.clearInterval(timer)},[connection?.state]);
 const run=async(name:string,action:()=>Promise<void>)=>{setPending(name);setError('');try{await action()}catch(error){setError(failure(error))}finally{setPending('')}};
 const list=()=>void run('models',async()=>{const response=await request<{models:{id:string}[];catalog_live:boolean}>(prefix+'codex/models',{});setModels(response.models.map(row=>row.id));setLive(response.catalog_live);setModel(value=>value||response.models[0]?.id||'')});
 return <div className="ui-settings-fields">
  <p className="ui-field-hint">ChatGPT 계정으로 로그인하고 사용할 모델을 선택합니다. Hermes 대화·기억·도구와 총괄 기능을 그대로 사용하며, ChatGPT 계정의 이용 한도를 사용합니다.</p>
  <Status tone={connection?.connected?'good':'idle'}>{connection?.connected?'ChatGPT 연결됨':connection?.state==='pending'?'로그인 대기 중':'로그인 필요'}</Status>
  <div className="ui-settings-actions"><Button disabled={disabled||!!pending||connection?.state==='pending'} busy={pending==='login'} onClick={()=>void run('login',async()=>setConnection(await request<Connection>(prefix+'codex/login',{})))}>ChatGPT로 로그인</Button><Button disabled={disabled||!!pending||!connection?.connected} busy={pending==='models'} onClick={list}>모델 목록 불러오기</Button></div>
  {connection?.state==='pending'&&<div className="ui-settings-notice" role="status"><p>브라우저에서 로그인한 뒤 다음 코드를 입력하세요. 약 15분 동안 유효합니다.</p><p><strong>{connection.code}</strong></p><a href={connection.url} target="_blank" rel="noreferrer">ChatGPT 로그인 화면 열기 ↗</a></div>}
  <label>사용할 모델<Input list="hermes-codex-models" value={model} disabled={disabled||!!pending} onChange={event=>setModel(event.target.value)} placeholder="로그인 후 모델 목록을 불러오세요"/></label>
  <datalist id="hermes-codex-models">{models.map(id=><option key={id} value={id}/>)}</datalist>
  {!!models.length&&<p className="ui-field-hint">{live?'계정에서 조회한 모델 목록입니다.':'임시 모델 목록입니다. 실제 사용 가능 여부는 첫 응답 완료로 확인합니다.'}</p>}
  <Button tone="primary" disabled={disabled||!!pending||!connection?.connected||!model.trim()} busy={pending==='select'} onClick={()=>void run('select',()=>onSelect(model.trim()))}>이 모델 사용</Button>
  <ErrorMessage message={error||connection?.error||''}/>
 </div>;
}
