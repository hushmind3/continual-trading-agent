import {useState} from 'react';
import {CheckCircle2,Play,Wallet,Download} from 'lucide-react';
import {useOperations} from '../data/Operations';
import type {Currency,Preflight} from '../data/types';
import {Button,Empty,ErrorMessage,Skeleton,Sparkline,Tabs} from '../ui/Primitives';
import {Panel,KeyValues} from '../ui/Panel';
import {Capability} from '../ui/Capability';
import {date,money,number} from '../ui/format';
import {ResultTable} from './portfolio/ResultTable';
import {PaperAccounts} from './portfolio/PaperAccounts';
export function PortfolioWorkspace(){const {state:s,execute,pending}=useOperations();const [currency,setCurrency]=useState<Currency>('USD'),[tab,setTab]=useState('weights'),[error,setError]=useState(''),[check,setCheck]=useState<Preflight|null>(null),[message,setMessage]=useState('');if(!s)return <Skeleton/>;
 const evaluation=s.evaluation,knownCurrency=evaluation.report.currency;
 const points=knownCurrency===currency?evaluation.points:[],first=points[0]?.value,last=points.at(-1)?.value;
 const body={currency:s.model.identity.currency||currency,symbols:s.model.identity.symbols||[],resume:false};
 const act=async(path:string)=>{setError('');try{if(path==='preflight/backtest')setCheck(await execute<Preflight>(path,body));else{const r=await execute<{message:string}>(path,body);setMessage(r.message);setCheck(null)}}catch(e){setError(e instanceof Error?e.message:'평가 실패')}};
 return <div className="space-y-5"><div className="flex flex-wrap items-center justify-between gap-3"><Tabs items={[{id:'KRW',label:'국내주식 · KRW'},{id:'USD',label:'미국주식 · USD'}]} value={currency} onChange={v=>setCurrency(v as Currency)}/><span className="text-xs text-slate-400">원화·달러 평가 결과는 합산하지 않습니다.</span></div>
 <PaperAccounts key={currency} currency={currency}/>
 <Capability name="paper_accounts" label="KRW · USD 가상매매"/>
 <section className="grid gap-6 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200/50 lg:grid-cols-[1fr_1.15fr]"><div><h2 className="flex items-center gap-2 text-sm font-bold"><Wallet size={17}/>{currency} 백테스트 포트폴리오</h2><p className="mt-4 text-xs text-slate-400">마지막 실제 평가 가치</p><p className="mt-2 text-4xl font-bold tabular-nums">{last!=null?money(last,currency):'평가 결과 없음'}</p><KeyValues items={[['처음 평가 가치',first!=null?money(first,currency):'없음'],['평가 관측',number(points.length,0)],['평가 통화',knownCurrency||'기록 없음'],['정책 종목',evaluation.report.symbols?.join(', ')||'미기록']]}/></div><div><p className="mb-3 text-xs text-slate-400">실제 저장된 포트폴리오 가치 추이 · {date(evaluation.file.modified)}</p><Sparkline values={points.map(p=>p.value)} up={last!=null&&first!=null&&last>=first} height={130}/>{!points.length&&<Empty title="이 통화로 확인된 평가 결과가 없습니다." detail={evaluation.file.exists&&!knownCurrency?'CSV는 있지만 평가 통화 메타데이터가 없어 금액을 해당 계좌로 표시하지 않습니다.':'현재 정책으로 백테스트를 실행하세요.'}/>}</div></section>
 <Panel title="공식 BacktestEngine 평가" description="저장된 현재 SAC 정책에 최근 365일의 테스트 구간을 적용합니다."><KeyValues items={[['저장 정책 통화',s.model.identity.currency],['저장 정책 종목',s.model.identity.symbols?.join(', ')],['호환 여부',s.model.compatible?'호환':'현재 설정과 미호환'],['수수료·비중 처리',s.settings.notes[1]]]}/><div className="mt-4 flex flex-wrap gap-3"><Button disabled={s.job.running||!s.model.file.exists} busy={pending.has('preflight/backtest')} onClick={()=>void act('preflight/backtest')}><CheckCircle2 size={15}/>평가 전 검사</Button><Button tone="primary" disabled={s.job.running||!check?.ok} busy={pending.has('backtest')} onClick={()=>void act('backtest')}><Play size={15}/>SAC 백테스트 실행</Button></div>{check&&!check.ok&&<div className="my-4 rounded-xl bg-amber-50 p-4 text-xs leading-6 text-amber-800">{check.errors.map((e,i)=><p key={i}>{e}</p>)}</div>}<div className="mt-4"><ErrorMessage message={error}/>{message&&<p className="text-sm text-emerald-700">{message}</p>}</div>{Object.entries(evaluation.report.strategies||{}).map(([name,metrics])=><div className="mt-6" key={name}><h3 className="text-sm font-bold">{name}</h3><KeyValues items={Object.entries(metrics).map(([k,v])=>[k,number(v,6)])}/></div>)}</Panel>
 <Panel title="포트폴리오 가중치 · 거래 원장" description="실제 증권 계좌의 보유 주식과 구분 · 원본 평가 결과"><div className="mb-5 flex flex-wrap items-center justify-between gap-4"><Tabs value={tab} onChange={setTab} items={[{id:'weights',label:'포트폴리오 가중치'},{id:'trades',label:'백테스트 거래'}]}/>{evaluation.file.exists&&<a className="flex items-center gap-2 text-xs text-blue-600" href={'/api/download/backtest_'+(tab==='weights'?'weights':'trades')+'.csv'} download><Download size={14}/>CSV 다운로드</a>}</div><ResultTable key={tab} kind={tab as 'weights'|'trades'}/></Panel>
 </div>;
}
