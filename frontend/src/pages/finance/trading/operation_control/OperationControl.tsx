import {LearningProgress} from './LearningProgress';
import {ArrowUpRight,Boxes,BrainCircuit,GraduationCap,Radio} from 'lucide-react';
import {useOperations} from '../../../../data/Operations';
import {Skeleton,Meter} from '../../../../ui/Primitives';
import {CollapsiblePanels} from '../../../../ui/Panel';
import {bytes,number,date} from '../../../../ui/format';
import {ServiceProgress} from '../../../../ui/ServiceProgress';
import {SystemControls} from '../../../../ui/SystemControls';

export function OperationControl(){
 const {state:s}=useOperations();
 if(!s)return <Skeleton/>;
 const operation=s.operations,broker=operation?.broker,receiving=Boolean(operation?.controls.feed),connected=Boolean(broker?.connected);
 const currencies=['KRW','USD'] as const;
 const policyName=(currency:'KRW'|'USD')=>{
  const policy=operation?.policies?.[currency];
  if(!policy)return null;
  return s.checkpoints.find(item=>item.path===policy.path)?.name??policy.path.split(/[\\/]/).filter(Boolean).pop()??'선택된 모델';
 };
 const learningActive=Boolean(operation?.controls.learning),learning=operation?.learning;
 const quoteState=connected&&receiving?'연결됨':receiving?'연결 대기':'수신 중지';
 const quoteTone=connected&&receiving?'good':receiving?'warn':'idle';
 const resource=s.resources;
 return <div className="ops-workspace">
  <SystemControls/>
  <section className="ops-overview" aria-labelledby="ops-current-state">
   <header className="ops-overview-head"><h2 id="ops-current-state">현재 상태</h2><span>실시간</span></header>
   <div className="ops-state-grid">
    <div className="ops-state-item">
     <div className="ops-state-label"><Radio size={16}/><span>시세 연결</span></div>
     <strong className={'ops-state-value ops-value-'+quoteTone}>{quoteState}</strong>
     <span className="ops-state-meta">{connected&&broker?.last_quote_utc?'최근 '+date(broker.last_quote_utc):number(broker?.quote_events??0,0)+'건 수신'}</span>
    </div>
    {currencies.map(currency=>{
     const policy=operation?.policies?.[currency],name=policyName(currency);
     return <div className="ops-state-item" key={currency}>
      <div className="ops-state-label"><BrainCircuit size={16}/><span>{currency} 모델</span></div>
      {name?<><strong className="ops-state-value ops-model-name" title={name}>{name}</strong><span className="ops-state-meta">{policy?.loaded?'로드 완료':'선택됨 · 로드 대기'}</span></>:<><strong className="ops-state-value ops-value-idle">미선택</strong><a href="#finance/policy_learning" className="ops-state-action">모델 선택 <ArrowUpRight size={12}/></a></>}
     </div>;
    })}
    <div className="ops-state-item">
     <div className="ops-state-label"><GraduationCap size={16}/><span>지속 학습</span></div>
     <strong className={'ops-state-value '+(learningActive?'ops-value-good':'ops-value-idle')}>{learningActive?learning?.status??operation?.feed.learning_status??'대기 중':'중지됨'}</strong>
     <a href="#finance/policy_learning" className="ops-state-action">학습 관리 <ArrowUpRight size={12}/></a>
    </div>
   </div>
  </section>
  <details className="ops-more">
   <summary>자세한 상태 보기 <span aria-hidden="true">⌄</span></summary>
   <div className="ops-more-content">
    <CollapsiblePanels.Provider value={false}><LearningProgress/></CollapsiblePanels.Provider>
    <section className="ops-stages" aria-label="운영 단계">
     {([{role:'feed',title:'시세 수신',Icon:Radio},{role:'experts',title:'모델 분석',Icon:Boxes},{role:'agent',title:'매매 판단',Icon:BrainCircuit},{role:'learner',title:'지속 학습',Icon:GraduationCap}] as const).map(({role,title,Icon})=><div className="ops-stage" key={role}><div className="ops-stage-title"><Icon size={17}/><span>{title}</span></div><ServiceProgress role={role}/></div>)}
    </section>
    <details className="ops-resources"><summary>실행 장치</summary>
     <div className="ops-resources-grid">
      <div><span>RAM</span><strong>{bytes(resource.ram_used_bytes)} / {bytes(resource.ram_total_bytes)}</strong>{resource.ram_total_bytes>0&&<Meter value={resource.ram_used_bytes/resource.ram_total_bytes*100}/>}</div>
      <div><span>{resource.gpu.name||'GPU'}</span><strong>{bytes(resource.gpu.used_bytes)} / {bytes(resource.gpu.total_bytes)}</strong>{Boolean(resource.gpu.total_bytes)&&<Meter value={(resource.gpu.used_bytes||0)/resource.gpu.total_bytes*100}/>}</div>
     </div>
    </details>
   </div>
  </details>
 </div>;
}
