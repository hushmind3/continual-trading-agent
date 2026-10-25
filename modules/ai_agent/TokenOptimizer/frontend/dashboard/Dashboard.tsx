import {useEffect,useState} from 'react';
import {RefreshCw} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,Empty,ErrorMessage,Status} from '@platform/ui/Primitives';
import {Panel,KeyValues} from '@platform/ui/Panel';
import {DataTable} from '@platform/ui/DataTable';

type Usage={period_days:number|null;session_count:number|null;total_input_tokens:number|null;total_output_tokens:number|null;
 total_fresh_input:number|null;total_cache_read:number|null;total_cache_create:number|null;total_messages:number|null;
 total_cost_usd:number|null;cost_coverage_pct:number|null};
type Day={date:string;sessions:number;total_input:number;total_output:number};
type Snapshot={collected_at:string;version:string;usage:Usage;startup:{overhead_tokens:number|null;overhead_pct:number|null};
 daily:Day[];rtk:{available:boolean;error:string|null;summary:{total_commands:number|null;total_input:number|null;
 total_output:number|null;total_saved:number|null;avg_savings_pct:number|null}|null}};
const number=(value:number|null|undefined)=>value==null?'미집계':value.toLocaleString('ko-KR');
export function Dashboard(){
 const [data,setData]=useState<Snapshot>(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{let cancelled=false;setBusy(true);
  request<Snapshot>('ai_agent/TokenOptimizer/dashboard',{},'GET').then(value=>{if(!cancelled)setData(value)})
   .catch(reason=>{if(!cancelled)setError(reason instanceof Error?reason.message:String(reason))})
   .finally(()=>{if(!cancelled)setBusy(false)});return()=>{cancelled=true};},[]);
 async function refresh(){setBusy(true);setError('');try{setData(await request<Snapshot>('ai_agent/TokenOptimizer/dashboard',{refresh:true},'GET'))}
  catch(reason){setError(reason instanceof Error?reason.message:String(reason))}finally{setBusy(false)}}
 const usage=data?.usage,rtk=data?.rtk.summary;
 return <div className="space-y-6">
  <header className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm text-slate-500">최근 7일의 Codex 사용 기록과 명령 출력 절감 현황입니다.</p></div>
   <Button busy={busy} onClick={()=>void refresh()}><RefreshCw size={16}/>새로고침</Button></header>
  {error&&<ErrorMessage message={error}/>}
  {!data?<Empty title={busy?'토큰 사용 기록을 불러오고 있습니다.':'사용 기록을 불러오지 못했습니다.'}/>:<>
   <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[
    ['새 입력 토큰',usage?.total_fresh_input,'캐시를 제외하고 새로 전달한 입력입니다.'],
    ['캐시 재사용 토큰',usage?.total_cache_read,'이전 입력을 캐시에서 재사용한 누적량입니다.'],
    ['출력 토큰',usage?.total_output_tokens,'모델이 생성한 출력의 누적량입니다.'],
    ['기록된 세션',usage?.session_count,'기간에 포함된 실제 Codex 세션 수입니다.'],
   ].map(([title,value,detail])=><Panel key={String(title)} title={String(title)} description={String(detail)}>
    <p className="break-words text-3xl font-semibold tabular-nums">{number(value as number|null|undefined)}</p></Panel>)}</div>
   <div className="grid gap-6 xl:grid-cols-2">
    <Panel title="사용량 집계" description="누적 입력에는 캐시 재사용이 포함됩니다. API 가격 환산은 구독 요금이나 실제 청구액이 아닙니다.">
     <KeyValues items={[
      ['전체 입력 토큰',number(usage?.total_input_tokens)],['기록된 메시지',number(usage?.total_messages)],
      ['API 가격 환산 추정',usage?.total_cost_usd==null?'미집계':new Intl.NumberFormat('ko-KR',{style:'currency',currency:'USD'}).format(usage.total_cost_usd)],
      ['가격 계산 가능 비율',usage?.cost_coverage_pct==null?'미집계':number(usage.cost_coverage_pct)+'%'],
     ]}/><p className="mt-4 text-xs text-slate-500">API 가격 환산은 참고용 추정이며 실제 청구액이 아닙니다.</p>
    </Panel>
    <Panel title="최적화 현황" description="초기 지침은 도구의 추정치입니다. RTK 절감량은 명령 출력에 한정되며 전체 모델 사용량의 절감률과 다릅니다.">
     <KeyValues items={[
      ['초기 지침 추정',number(data.startup.overhead_tokens)+' 토큰'],
      ['초기 문맥 추정 비중',data.startup.overhead_pct==null?'미집계':number(data.startup.overhead_pct)+'%'],
      ['RTK 처리 명령',rtk?number(rtk.total_commands):'미집계'],['명령 출력 추정 절감',rtk?number(rtk.total_saved)+' 토큰':'미집계'],
      ['명령 출력 추정 절감률',rtk?.avg_savings_pct==null?'미집계':number(rtk.avg_savings_pct)+'%'],
      ['Token Optimizer',data.version],
     ]}/>{data.rtk.error&&<ErrorMessage message={data.rtk.error}/>}
    </Panel>
   </div>
   <Panel title="일별 사용 기록" description="설치된 Token Optimizer가 Codex 기록에서 집계한 실제 일별 입력·출력입니다.">
    {data.daily.length?<DataTable items={data.daily} label="일별 토큰 사용 기록" keyFor={day=>day.date} showControls={false} columns={[
     {key:'date',label:'날짜',render:day=>day.date},{key:'sessions',label:'세션',render:day=>number(day.sessions)},
     {key:'input',label:'입력 · 캐시 포함',render:day=>number(day.total_input)},
     {key:'output',label:'출력',render:day=>number(day.total_output)},
    ]}/>:<Empty title="최근 7일의 사용 기록이 없습니다."/>}
   </Panel>
   <footer className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
    <Status tone="ok">공식 도구 집계</Status><span>집계 시각 {new Date(data.collected_at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})} · 한국 시간</span>
   </footer>
  </>}
 </div>;
}
