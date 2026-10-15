import {memo} from 'react';
import {Check,ChevronDown,Loader2,Wrench,TriangleAlert,Info,Clock3,Activity,Zap,ArrowDownToLine} from 'lucide-react';
import {contentText,type Message,type Job,type Metrics} from '../types';
import {toolLabel,eventSummary} from '../labels';
import {MessageBody,CopyButton} from './MessageBody';

type Call={id?:string;function?:{name?:string;arguments?:string}};
type Step={id:string;name:string;args:string;result?:unknown};
type Block={kind:'message';index:number;message:Message}|{kind:'tools';index:number;steps:Step[]};
function failed(content:unknown){try{const r=JSON.parse(contentText(content));return !!r.error||r.success===false||(typeof r.exit_code==='number'&&r.exit_code!==0)}catch{return false}}
function blocks(messages:Message[]):Block[]{
 const output:Block[]=[];let steps:Step[]=[];let first=0;
 const flush=()=>{if(steps.length){output.push({kind:'tools',index:first,steps});steps=[]}};
 for(let i=0;i<messages.length;i++){
  const m=messages[i],text=contentText(m.content),calls=(m.tool_calls??[]) as Call[];
  if(m.role==='tool'){if(!steps.length)first=i;steps.push({id:'orphan-'+i,name:m.name??'도구',args:'',result:m.content});continue}
  if(!['user','assistant'].includes(m.role))continue;
  if(text.trim()){flush();output.push({kind:'message',index:i,message:m})}
  if(calls.length){if(!steps.length)first=i;const results:Message[]=[];let j=i+1;for(;j<messages.length&&messages[j].role==='tool';j++)results.push(messages[j]);for(let n=0;n<calls.length;n++){const c=calls[n],r=results.find(r=>r.tool_call_id&&r.tool_call_id===c.id)??results[n];steps.push({id:c.id??i+'-'+n,name:c.function?.name??'도구',args:c.function?.arguments??'',result:r?.content})}i=j-1}
 }
 flush();return output;
}
function ToolGroup({steps}:{steps:Step[]}){
 const errors=steps.filter(s=>s.result!==undefined&&failed(s.result)).length,names=[...new Set(steps.map(s=>toolLabel(s.name)))];
 return <details className={'ha-tool-group '+(errors?'has-errors':'')}><summary><Wrench size={15}/><span>작업 기록 <b>{steps.length}</b></span><small>{names.slice(0,2).join(' · ')}{names.length>2?' 외 '+(names.length-2)+'개':''}</small>{errors>0&&<em>오류 {errors}</em>}<ChevronDown size={14}/></summary><div className="ha-tool-steps">{steps.map(s=><details className="ha-tool-step" key={s.id}><summary>{s.result===undefined?<Wrench size={14}/>:failed(s.result)?<TriangleAlert size={14}/>:<Check size={14}/>}<b>{toolLabel(s.name)}</b><span>{s.result===undefined?'호출 기록':failed(s.result)?'오류 결과':'결과 수신'}</span><ChevronDown size={12}/></summary><div><small>요청</small><pre>{s.args||'별도 입력 없음'}</pre>{s.result!==undefined&&<><small>도구 결과</small><pre>{contentText(s.result)}</pre></>}</div></details>)}</div></details>;
}
export const Transcript=memo(function Transcript({messages}:{messages:Message[]}){
 return <>{blocks(messages).map(block=>block.kind==='tools'?<ToolGroup key={'tools-'+block.index} steps={block.steps}/>:<article key={'message-'+block.index} className={'hermes-message '+block.message.role}>{block.message.role==='assistant'&&<div className="ha-assistant-mark" aria-label="헤르메스">✳</div>}<div className="ha-message-content"><MessageBody text={contentText(block.message.content)} user={block.message.role==='user'}/>{block.message.role==='assistant'&&<div className="ha-message-actions"><CopyButton text={contentText(block.message.content)} label="답변 복사"/></div>}</div></article>)}</>;
});
const number=(n?:number)=>n==null?'—':n.toLocaleString('ko-KR');
export function RuntimeMetrics({metrics}:{metrics?:Metrics}){
 const m=metrics,percent=m?.context_limit&&m.context_tokens!=null?Math.min(100,m.context_tokens/m.context_limit*100):undefined;
 return <div className="hermes-runtime-metrics" aria-label="모델 실행 정보"><div className="ha-context" title="엔진이 보고한 최근 입력 컨텍스트"><Activity size={13}/><span>컨텍스트</span><b>{number(m?.context_tokens)}<i> / {number(m?.context_limit)}</i></b>{percent!=null&&<meter aria-label="컨텍스트 사용률" min={0} max={100} value={percent}/>}</div>{m?.generation_tps!=null&&<div title="실제 생성 토큰 증가량을 측정 간격으로 나눈 최근 속도"><Zap size={13}/><b>{m.generation_tps} tok/s</b></div>}{m?.elapsed_seconds!=null&&m.elapsed_seconds>0&&<div><Clock3 size={13}/><b>{Math.round(m.elapsed_seconds)}초</b></div>}<details className="ha-metrics-detail"><summary aria-label="실행 정보 자세히 보기"><Info size={14}/><span>실행 정보</span></summary><dl><dt>입력 토큰 · 누적</dt><dd>{number(m?.input_tokens)}</dd><dt>출력 토큰 · 누적</dt><dd>{number(m?.output_tokens)}</dd><dt>모델 요청</dt><dd>{number(m?.api_calls)}</dd><dt>컨텍스트 사용률</dt><dd>{percent==null?'미측정':percent.toFixed(1)+'%'}</dd><dt>생성 속도</dt><dd>{m?.generation_tps==null?'측정 대기':m.generation_tps+' tok/s'}</dd></dl><p>현재 엔진의 보고 값입니다. 속도는 최근 측정 구간이며 미수신 값은 —로 표시합니다.</p></details></div>;
}
export function CurrentActivity({job,active}:{job?:Job;active:boolean}){
 const event=[...(job?.events??[])].reverse().find(e=>['tool_start','tool_complete','starting','autonomy_decision'].includes(e.name));
 let detail='';try{const d=JSON.parse(event?.detail??'null');if(Array.isArray(d)){const a=d.find(v=>v&&typeof v==='object'&&!Array.isArray(v));detail=String(a?.command??a?.url??a?.action??a?.path??'')}}catch{}
 if(!active&&!['failed','stopped','paused'].includes(job?.state??''))return null;
 return <div className={'hermes-current-activity '+(active?'is-active':'')} role="status">{active?<Loader2 size={14} className="hermes-spin"/>:<TriangleAlert size={14}/>}<b>{active?(job?.phase==='tool'?'도구 실행 중':'응답 생성 중'):job?.state==='failed'?'작업 실패':job?.state==='stopped'?'중지됨':'일시정지'}</b>{event&&<span>{eventSummary(event.name,event.detail)}{detail?' · '+detail:''}</span>}</div>;
}
export function ActivityTimeline({job}:{job?:Job}){
 const rows:{id:string;name:string;time:number;detail:string;result?:string;state:string}[]=[];
 for(const [i,event] of (job?.events??[]).entries()){
  let data:unknown;try{data=JSON.parse(event.detail)}catch{data=event.detail}
  if((event.name==='tool_start'||event.name==='tool_complete')&&Array.isArray(data)){
   const id=String(data[0]??i),name=String(data[1]??'도구'),args=data[2];
   let row=rows.find(r=>r.id===id);if(!row){row={id,name:toolLabel(name),time:event.time,detail:typeof args==='object'?JSON.stringify(args,null,2):String(args??''),state:'running'};rows.push(row)}
   if(event.name==='tool_complete'){row.result=contentText(data[3]);row.state=failed(data[3])?'error':'received'}
  }
 }
 return <div className="ha-activity-timeline">{rows.length?rows.map((row,i)=><details key={row.id} className={'ha-activity-item '+row.state}><summary><span className="ha-step-dot">{row.state==='running'?<Loader2 size={13} className="hermes-spin"/>:row.state==='error'?<TriangleAlert size={13}/>:<Check size={13}/>}</span><span><b>{row.name}</b><small>{i+1}번째 단계 · {row.state==='running'?'진행 중':row.state==='error'?'오류 결과':'결과 수신'}</small></span><ChevronDown size={13}/></summary><div><small>요청</small><pre>{row.detail}</pre>{row.result&&<><small>결과</small><pre>{row.result}</pre></>}</div></details>):<div className="ha-panel-empty"><Wrench size={27}/><b>실행 과정을 한눈에</b><p>대화에서 작업을 시작하면 사용한 도구와 실제 결과가 여기에 표시됩니다.</p></div>}{!!job?.events.length&&<details className="ha-raw-events"><summary><ArrowDownToLine size={13}/>전체 이벤트 · {job.events.length}개</summary><pre>{JSON.stringify(job.events,null,2)}</pre></details>}</div>;
}
