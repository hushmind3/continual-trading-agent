import type {AccountEquityPoint,Currency} from '@platform/data/types';
import {Panel} from '@platform/ui/Panel';
import {money,date} from '@platform/ui/format';

export function AccountEquityHistory({history,currency}:{history?:AccountEquityPoint[];currency:Currency}){
 const points=(history??[]).map(point=>({...point,time:typeof point.date==='string'?Date.parse(point.date.replace(' ','T')+(/[zZ]|[+-]\d\d:\d\d$/.test(point.date)?'':'Z')):NaN}))
  .filter(point=>Number.isFinite(point.time)&&Number.isFinite(point.nav)).sort((a,b)=>a.time-b.time).slice(-200);
 if(points.length<2)return null;
 const first=points[0],last=points[points.length-1],low=Math.min(...points.map(p=>p.nav)),high=Math.max(...points.map(p=>p.nav));
 const padding=(high-low||Math.abs(high)*.02||1)*.12,min=low-padding,max=high+padding;
 const x=(time:number)=>12+(time-first.time)/(last.time-first.time||1)*576,y=(value:number)=>168-(value-min)/(max-min)*144;
 const moment=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
 const line=points.map(p=>x(p.time)+','+y(p.nav)).join(' ');
 return <Panel title="평가자산 추이" className="account-equity-history" collapsible={false}>
  <div className="account-history-labels"><span>최고 {money(high,currency)}</span><span>최저 {money(low,currency)}</span></div>
  <svg viewBox="0 0 600 192" role="img" aria-label={'저장된 평가자산 '+points.length+'개 시점의 추이. 시작 '+money(first.nav,currency)+', 마지막 '+money(last.nav,currency)}>
   {[24,96,168].map(row=><line key={row} x1="12" x2="588" y1={row} y2={row} stroke="currentColor" className="text-slate-200" strokeDasharray="4 5"/>)}
   <polyline points={line} fill="none" stroke="currentColor" className="text-blue-600" strokeWidth="2.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round"/>
   <circle cx={x(last.time)} cy={y(last.nav)} r="4" fill="currentColor" className="text-blue-600"/>
  </svg>
  <div className="account-history-dates"><span>{date(first.date)}</span><span>{date(last.date)}</span></div>
  <p className="account-history-caption">최근 {points.length}개 저장 시점 · 시점 사이를 잇는 선입니다. 현재 시세나 실계좌 수익을 표시하지 않습니다.</p>
  <details className="policy-storage-details"><summary>평가 기록 보기</summary><div className="account-history-table" tabIndex={0} role="region" aria-label="저장된 평가 기록"><table><thead><tr><th scope="col">저장 시점</th><th scope="col">평가자산</th></tr></thead><tbody>{points.map((point,index)=><tr key={index}><td>{moment.format(point.time)}</td><td>{money(point.nav,currency)}</td></tr>)}</tbody></table></div></details>
 </Panel>;
}
