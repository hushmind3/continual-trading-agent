import {LearningProgress} from './LearningProgress';
import {ArrowRight,Boxes,Database,GraduationCap,Radio} from 'lucide-react';
import {useOperations} from '../../../../data/Operations';
import {Skeleton,Meter,Status} from '../../../../ui/Primitives';
import {Panel} from '../../../../ui/Panel';
import {bytes,number,date} from '../../../../ui/format';
import {ServiceProgress} from '../../../../ui/ServiceProgress';
import {Capability} from '../../../../ui/Capability';
import {SystemControls} from '../../../../ui/SystemControls';
export function OperationControl(){
 const {state:s}=useOperations();if(!s)return <Skeleton/>;
 const r=s.resources,broker=s.operations?.broker,connected=Boolean(broker?.connected),receiving=Boolean(s.operations?.controls.feed);
 const connectionLabel=!receiving?'수신 중지':connected?'실제 연결됨':broker?.transport_status==='reconnecting'?'재연결 대기':'연결 대기';
 return <div className="operations-layout">
  <SystemControls/>
  <div className="operations-overview">
   <Panel title="키움 시세 연결" actions={<Status tone={!receiving?'idle':connected?'good':'warn'}>{connectionLabel}</Status>}>
    <dl className="operations-connection-metrics"><div><dt className="operations-stat-label">실제 시세 수신</dt><dd className="operations-stat-value">{number(broker?.quote_events??0,0)} <span className="text-xs font-normal text-slate-400">건</span></dd></div><div><dt className="operations-stat-label">최근 시세</dt><dd className="operations-stat-value operations-stat-value-small">{date(broker?.last_quote_utc)}</dd></div></dl>
    <div className="operations-region-row"><span>국내<strong>{receiving&&broker?.kr_connected?'연결됨':'미연결'}</strong></span><span>미국<strong>{receiving&&broker?.us_connected?'연결됨':'미연결'}</strong></span></div>
    {receiving&&!connected&&!!broker?.reconnect_in_seconds&&<p className="mt-3 text-xs text-amber-700">{String(broker.reconnect_in_seconds)}초 후 연결 재시도</p>}
    <p className="mt-3 text-xs leading-5 text-slate-400">최근 시세는 실제 가격 이벤트 기준입니다. 서버 연결과 시세 수신 상태는 구분합니다.</p>
   </Panel>
   <Panel title="시스템 리소스">
    <div className="operations-resource-grid"><div><p className="operations-stat-label">시스템 RAM</p><p className="operations-stat-value">{bytes(r.ram_used_bytes)} <span className="text-xs font-normal text-slate-400">/ {bytes(r.ram_total_bytes)}</span></p><div className="mt-3"><Meter value={r.ram_used_bytes/r.ram_total_bytes*100}/></div><p className="mt-2 text-xs text-slate-400">사용 가능 {bytes(r.ram_available_bytes)}</p></div><div><p className="operations-stat-label">{r.gpu.name||'GPU 측정 없음'}</p><p className="operations-stat-value">{bytes(r.gpu.used_bytes)} <span className="text-xs font-normal text-slate-400">/ {bytes(r.gpu.total_bytes)}</span></p>{r.gpu.total_bytes&&<div className="mt-3"><Meter value={(r.gpu.used_bytes||0)/r.gpu.total_bytes*100}/></div>}<p className="mt-2 text-xs text-slate-400">GPU 사용률 {number(r.gpu.utilization_percent)}%</p></div></div>
    <p className="operations-resource-footnote">CPU {number(r.cpu_percent)}% · 디스크 여유 {bytes(r.disk_free_bytes)}</p>
   </Panel>
  </div>
  <LearningProgress/>
  <section className="operations-flow"><div className="operations-flow-heading"><div><h2>운영 흐름</h2><p>FinRL 환경 · 선택한 Stable-Baselines3 알고리즘 · 동결 Expert 관측</p></div><a className="operations-flow-link" href="#finance/policy_learning">학습 화면 <span aria-hidden="true">→</span></a></div><div className="grid grid-cols-2 lg:grid-cols-4">
   {([{role:'feed',title:'시장 입력',Icon:Radio},{role:'experts',title:'Expert 분석',Icon:Boxes},{role:'agent',title:'선택 정책',Icon:Database},{role:'learner',title:'중앙 모델 학습',Icon:GraduationCap}] as const).map(({role,title,Icon},i)=><div key={role} className="operations-flow-step"><Icon size={20}/><div className="min-w-0"><h3>{title}</h3><div className="mt-2"><ServiceProgress role={role}/></div></div>{i<3&&<ArrowRight size={14} className="absolute right-0 top-9 hidden text-slate-200 lg:block"/>}</div>)}
  </div></section>
  <Panel title="제공 기능" description="현재 백엔드의 기능 지원 상태" defaultCollapsed><div className="grid gap-3 sm:grid-cols-2"><Capability name="learning" label="정책 학습"/><Capability name="expert_selection" label="Frozen Expert"/><Capability name="live_feed" label="실시간 시세"/><Capability name="paper_accounts" label="독립 가상계좌"/></div></Panel>
 </div>;
}
