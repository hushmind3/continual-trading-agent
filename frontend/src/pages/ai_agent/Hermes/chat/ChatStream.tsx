import {Check,ChevronDown,Loader2,Wrench} from 'lucide-react';
import {contentText,type Message,type Job,type Metrics} from '../types';
import {toolLabel,eventSummary} from '../labels';
type Call={id?:string;function?:{name?:string;arguments?:string}};
function failed(content:unknown){try{const r=JSON.parse(contentText(content));return !!r.error||r.success===false||(typeof r.exit_code==='number'&&r.exit_code!==0)}catch{return false}}
export function Transcript({messages}:{messages:Message[]}){
 return <>{messages.map((message,index)=>{
  if(message.role==='tool')return null;
  if(!['user','assistant'].includes(message.role))return null;
  const calls=(message.tool_calls??[]) as Call[],text=contentText(message.content);
  const results:Message[]=[];for(let n=index+1;n<messages.length&&messages[n].role==='tool';n++)results.push(messages[n]);
  if(!text&&!calls.length)return null;
  return <div key={index} className="hermes-turn">{text&&<article className={'hermes-message '+message.role}><b>{message.role==='user'?'나':'헤르메스'}</b><pre>{text}</pre></article>}{calls.map((call,n)=>{const result=results.find(r=>r.tool_call_id&&r.tool_call_id===call.id)??results[n];const error=result&&failed(result.content);return <details className={'hermes-action-card '+(error?'is-error':'')} key={call.id??n}><summary>{result?<Check size={14}/>:<Wrench size={14}/>}<b>{toolLabel(call.function?.name??'도구')}</b><span>{result?(error?'오류 결과':'결과 확인'):'도구 호출'}</span><ChevronDown size={13}/></summary><div><small>요청</small><pre>{call.function?.arguments}</pre>{result&&<><small>결과</small><pre>{contentText(result.content)}</pre></>}</div></details>})}</div>;
 })}</>;
}
const number=(n?:number)=>n==null?'—':n.toLocaleString('ko-KR');
export function RuntimeMetrics({metrics}:{metrics?:Metrics}){
 const m=metrics,percent=m?.context_limit&&m.context_tokens!=null?Math.min(100,m.context_tokens/m.context_limit*100):undefined;
 return <div className="hermes-runtime-metrics" aria-label="모델 실행 정보"><div title="llama.cpp 슬롯 또는 Hermes 엔진이 보고한 최근 입력 컨텍스트"><span>컨텍스트</span><b>{number(m?.context_tokens)} / {number(m?.context_limit)}</b>{percent!=null&&<meter aria-label="컨텍스트 사용률" min={0} max={100} value={percent}/>}</div><div title="llama.cpp 생성 토큰 증가량을 실제 경과 시간으로 나눈 최근 측정값"><span>생성 속도</span><b>{m?.generation_tps==null?'측정 대기':m.generation_tps+' tok/s'}</b></div><div><span>누적 입력 / 출력</span><b>{number(m?.input_tokens)} / {number(m?.output_tokens)}</b></div><div><span>모델 요청</span><b>{number(m?.api_calls)}회</b></div><div><span>경과</span><b>{m?.elapsed_seconds==null?'—':Math.round(m.elapsed_seconds)+'초'}</b></div></div>;
}
export function CurrentActivity({job,active}:{job?:Job;active:boolean}){
 const event=[...(job?.events??[])].reverse().find(e=>e.name==='tool_start'||e.name==='tool_complete'||e.name==='starting'||e.name==='autonomy_decision');
 let detail='';try{const data=JSON.parse(event?.detail??'null');if(Array.isArray(data)){const a=data.find(v=>v&&typeof v==='object'&&!Array.isArray(v));detail=String(a?.command??a?.url??a?.action??a?.path??'')}}catch{}
 return <div className={'hermes-current-activity '+(active?'is-active':'')} role="status">{active?<Loader2 size={15} className="hermes-spin"/>:<Check size={15}/>}<b>{active?(job?.phase==='tool'?'도구 실행 중':'응답 생성·작업 진행 중'):job?.state==='failed'?'작업 실패':job?.state==='stopped'?'중지됨':job?.state==='paused'?'일시정지':job?'작업 완료':'작업 대기'}</b>{event&&<span>{eventSummary(event.name,event.detail)}{detail?' · '+detail:''}</span>}</div>;
}
