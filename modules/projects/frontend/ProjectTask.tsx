import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Input,Textarea,ErrorMessage,Status} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {McpTools} from './McpTools';
export function ProjectTask({projectId}:{projectId:string}){
 const [target,setTarget]=useState(''),[message,setMessage]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[connection,setConnection]=useState<{connected:boolean;tools:number}|null>(null),[advanced,setAdvanced]=useState(false);
 useEffect(()=>{let live=true;request<{connected:boolean;tools:number}>('projects/agent/connect',{id:projectId},'POST',100000).then(value=>{if(live)setConnection(value)}).catch(e=>{if(live)setError(String(e))});return()=>{live=false}},[projectId]);
 async function start(){setBusy(true);setError('');try{const result=await request<{session_id:string}>('projects/agent/start',{id:projectId,target,message},'POST',240000);sessionStorage.setItem('hermes.session',result.session_id);location.href='/#ai_agent/Hermes';location.reload()}catch(e){setError(String(e))}finally{setBusy(false)}}
 return <div className="min-h-0 flex-1 space-y-5 overflow-auto p-4"><Panel title="무엇을 해볼까요?" collapsible={false} actions={<Status tone={connection?.connected?'good':'idle'}>{connection?.connected?'에이전트 연결 · '+connection.tools+'개 도구':'자동 연결 중'}</Status>}><ErrorMessage message={error}/><form className="space-y-4" onSubmit={e=>{e.preventDefault();void start()}}><p className="text-sm text-slate-500">대상과 요청을 입력하면 에이전트가 이 프로젝트의 도구를 선택해 작업합니다. 과정과 결과는 대화에서 이어서 볼 수 있습니다.</p><Input aria-label="작업 대상" placeholder="분석할 파일 또는 폴더 경로" value={target} onChange={e=>setTarget(e.target.value)}/><Textarea aria-label="작업 요청" rows={5} placeholder="예: 이 Electron 앱의 검색 기능을 분석하고 한국어로 정리해 줘." required value={message} onChange={e=>setMessage(e.target.value)}/><Button tone="primary" type="submit" disabled={!message.trim()} busy={busy}>{busy?'모델 준비·작업 시작 중':'작업 시작'}</Button></form></Panel><Button variant="ghost" onClick={()=>setAdvanced(!advanced)}>{advanced?'도구 상세 닫기':'개발자용 도구 상세'}</Button>{advanced&&<McpTools projectId={projectId}/>}</div>;
}
