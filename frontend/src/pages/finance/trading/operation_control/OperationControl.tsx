import {LearningProgress} from './LearningProgress';
import {ArrowRight,Boxes,Database,GraduationCap,Radio,Cpu} from 'lucide-react';
import {useOperations} from '../../../../data/Operations';
import {Skeleton,Meter} from '../../../../ui/Primitives';
import {Panel} from '../../../../ui/Panel';
import {bytes,number,date} from '../../../../ui/format';
import {ServiceProgress} from '../../../../ui/ServiceProgress';
import {Capability} from '../../../../ui/Capability';
import {SystemControls} from '../../../../ui/SystemControls';
export function OperationControl(){const {state:s}=useOperations();if(!s)return <Skeleton/>;const r=s.resources,broker=s.operations?.broker;const connected=Boolean(broker?.connected),receiving=Boolean(s.operations?.controls.feed);
 return <div className="space-y-6">
  <SystemControls/>
  <section className="rounded-2xl bg-white px-6 py-4 shadow-sm ring-1 ring-slate-200/60" aria-label="실제 시세 연결 상태">
   <h2 className="text-sm font-bold">키움 시세 연결</h2>
   <p className={'mt-2 text-sm '+(connected?'text-emerald-700':receiving?'text-amber-700':'text-slate-500')}>{!receiving?'수신 중지':connected?'실제 연결됨':broker?.transport_status==='reconnecting'?'연결 끊김 · 재연결 대기':'연결 대기 · 시세 수신 미확인'}</p>
   <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-600"><span>국내 {receiving&&broker?.kr_connected?'연결됨':'미연결'}</span><span>미국 {receiving&&broker?.us_connected?'연결됨':'미연결'}</span><span>실제 시세 수신 {number(broker?.quote_events??0,0)}건</span><span>최근 시세 {date(broker?.last_quote_utc)}</span></div>
   {receiving&&!connected&&!!broker?.reconnect_in_seconds&&<p className="mt-2 text-xs text-amber-700">{String(broker.reconnect_in_seconds)}초 후 연결 재시도</p>}
   <p className="mt-2 text-xs text-slate-400">수신 실행과 서버 연결은 별도 상태입니다. 최근 시세 시각은 실제 가격 이벤트 기준입니다.</p>
  </section>
  <LearningProgress/>
  <section className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200/60"><div className="flex flex-wrap justify-between gap-4 border-b border-slate-100 px-6 py-4"><div><h2 className="text-base font-bold">공식 강화학습 운영</h2><p className="mt-1 text-xs text-slate-400">FinRL 환경 · 선택한 Stable-Baselines3 알고리즘 · 동결 Expert 관측</p></div><a className="text-sm text-blue-600" href="#finance/policy_learning">학습 화면 →</a></div><div className="grid grid-cols-2 lg:grid-cols-4">
  {([{role:'feed',title:'시장 입력',Icon:Radio,color:'text-blue-500'},{role:'experts',title:'Expert 분석',Icon:Boxes,color:'text-violet-500'},{role:'agent',title:'선택 정책',Icon:Database,color:'text-emerald-500'},{role:'learner',title:'공식 학습',Icon:GraduationCap,color:'text-amber-500'}] as const).map(({role,title,Icon,color},i)=><div key={role} className="relative flex gap-3 border-b border-slate-50 p-5"><Icon className={color+' mt-1 shrink-0'} size={22}/><div><h3 className="text-sm font-semibold">{title}</h3><div className="mt-2"><ServiceProgress role={role}/></div></div>{i<3&&<ArrowRight size={14} className="absolute right-0 top-9 hidden text-slate-200 lg:block"/>}</div>)}
  </div></section>
  <div className="grid gap-6"><section className="rounded-2xl bg-[#edf3ff] p-6"><h2 className="mb-5 flex items-center gap-2 text-sm font-bold"><Cpu size={17}/>실측 RAM · VRAM</h2><div className="grid gap-6 sm:grid-cols-2"><div><p className="text-xs text-slate-500">시스템 RAM</p><p className="my-3 text-xl font-bold">{bytes(r.ram_used_bytes)} <span className="text-xs font-normal text-slate-400">/ {bytes(r.ram_total_bytes)}</span></p><Meter value={r.ram_used_bytes/r.ram_total_bytes*100}/><p className="mt-2 text-xs text-slate-500">사용 가능 {bytes(r.ram_available_bytes)}</p></div><div><p className="text-xs text-slate-500">{r.gpu.name||'GPU 측정 없음'}</p><p className="my-3 text-xl font-bold">{bytes(r.gpu.used_bytes)} <span className="text-xs font-normal text-slate-400">/ {bytes(r.gpu.total_bytes)}</span></p>{r.gpu.total_bytes&&<Meter value={(r.gpu.used_bytes||0)/r.gpu.total_bytes*100} color="bg-violet-500"/>}<p className="mt-2 text-xs text-slate-500">GPU 사용률 {number(r.gpu.utilization_percent)}%</p></div></div><div className="mt-6 flex flex-wrap gap-6 border-t border-blue-200/40 pt-4 text-xs text-slate-500">CPU {number(r.cpu_percent)}% · 디스크 여유 {bytes(r.disk_free_bytes)}</div></section>
  </div>
  <Panel title="현재 제공 기능" description="과거 화면과 현재 백엔드의 지원 여부"><div className="grid gap-3 sm:grid-cols-2"><Capability name="learning" label="SAC 학습"/><Capability name="expert_selection" label="Frozen Expert"/><Capability name="live_feed" label="실시간 시세"/><Capability name="paper_accounts" label="독립 가상계좌"/></div></Panel>
 </div>;
}
