import {useEffect,useState} from 'react';
import {ArrowRight,Download,Play} from 'lucide-react';
import {useSystemState,useOperations} from '../data/Operations';
import {MarketScanner} from './MarketScanner';

type Step='data'|'train'|'backtest';
interface Defaults {revision:string;data_source:string;ticker_group:string;tickers:string[];train_start:string;train_end:string;trade_start:string;trade_end:string;indicators:string[];initial_amount:number;cost_pct:number;total_timesteps:number;algorithms:string[];environment:string;model_kwargs:Record<string,Record<string,unknown>>;scripts:{name:string;url:string}[]}
interface Run {job_id:string;action:string;status:string;error?:string;data_job_id?:string;training_job_id?:string;settings?:Record<string,unknown>;model_states?:Record<string,{status:string;num_timesteps?:number;error?:string}>;artifacts:{name:string;bytes:number;url:string}[];value?:{train_rows?:number;trade_rows?:number;stock_dimension?:number;columns?:string[];rows?:Record<string,unknown>[];total_rows?:number}}
interface Workspace {defaults:Defaults;runs:{stock_data:Run[];stock_train:Run[];stock_backtest:Run[]}}
const panel='rounded-2xl border border-slate-200 bg-white p-5 shadow-sm';
const input='mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-blue-400';
const button='inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40';
const statusLabel:Record<string,string>={queued:'대기',running:'실행 중',complete:'완료',succeeded:'완료',failed:'실패',stopped:'중지',interrupted:'실행 중단'};
const display=(value:unknown)=>value==null?'—':typeof value==='number'?value.toLocaleString('ko-KR'):String(value);

export function FinrlWorkspace({stage,onStageChange}:{stage?:Step;onStageChange?:(step:Step)=>void}={}){
 const api=useSystemState<Workspace>('finrl'),{state,execute,pending}=useOperations();
 const section=new URLSearchParams(location.hash.split('?')[1]||'').get('tab');const step:Step=stage??(section==='example-train'||location.hash.startsWith('#stock-training')?'train':section==='example-evaluate'||location.hash.startsWith('#backtest')?'backtest':'data');
 const selectedSymbol=new URLSearchParams(location.hash.split('?')[1]||'').get('symbol');
 useEffect(()=>{if(selectedSymbol)setFields(old=>({...old,tickers:selectedSymbol}))},[selectedSymbol]);
 const [fields,setFields]=useState<Record<string,string>>({}),[selection,setSelection]=useState<string[]|null>(null),[backtestSelection,setBacktestSelection]=useState<string[]|null>(null);
 const [dataId,setDataId]=useState(''),[trainingId,setTrainingId]=useState(''),[error,setError]=useState('');
 const defaults=api.data?.defaults,runs=api.data?.runs,job=state?.job;
 const busy=!!job?.running,stockJob=!!job?.action&&['stock_data','stock_train','stock_backtest'].includes(job.action);
 const dataset=runs?.stock_data.find(r=>r.job_id===dataId)??runs?.stock_data.find(r=>r.status==='complete');
 const training=runs?.stock_train.find(r=>r.job_id===trainingId)??runs?.stock_train[0];
 const backtest=runs?.stock_backtest.find(r=>r.training_job_id===training?.job_id);
 const models=selection??defaults?.algorithms??[],available=Object.keys(training?.model_states??{}).filter(name=>training?.model_states?.[name].status==='complete');
 const comparisons=backtestSelection??available;
 const active=step==='data'?runs?.stock_data[0]:step==='train'?training:backtest;
 const value=(key:string)=>fields[key]??(key==='tickers'?defaults?.tickers.join(', ')??'':key==='cost_pct'?String((defaults?.cost_pct??0)*100):String(defaults?.[key as keyof Defaults]??''));
 const change=(key:string,text:string)=>setFields(old=>({...old,[key]:text}));
 const start=async(action:Step)=>{
  if(!defaults)return;setError('');
  const parameters=action==='data'?{tickers:value('tickers').split(',').map(s=>s.trim()).filter(Boolean),train_start:value('train_start'),train_end:value('train_end'),trade_start:value('trade_start'),trade_end:value('trade_end')}:
   action==='train'?{data_job_id:dataset?.job_id,algorithms:models,total_timesteps:Number(value('total_timesteps')),initial_amount:Number(value('initial_amount')),cost_pct:Number(value('cost_pct'))/100}:
   {training_job_id:training?.job_id,algorithms:comparisons};
  try{const result=await execute<{job:{id:string}}>('framework/stock_'+action,parameters);if(action==='data')setDataId(result.job.id);if(action==='train'){setTrainingId(result.job.id);setBacktestSelection(null)}}catch(e){setError(e instanceof Error?e.message:'실행 요청 실패')}
 };
 const files=(run:Run|undefined)=><div className="space-y-2">{run?.artifacts?.length?run.artifacts.map(file=><a key={file.name} href={file.url} download className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-3 text-xs text-blue-600 hover:text-blue-100"><span className="break-all">{file.name}</span><Download size={14} className="shrink-0"/></a>):<p className="text-xs leading-6 text-slate-500">생성된 결과 파일이 없습니다.</p>}</div>;
 const metric=(name:string,text:unknown)=><div className={panel}><p className="text-xs text-slate-500">{name}</p><b className="mt-3 block text-xl text-slate-900">{display(text)}</b></div>;
 const script=defaults?.scripts[step==='data'?0:step==='train'?1:2];
 return <div className="space-y-6 text-slate-900">
  <div className="space-y-5">
   {(error||api.error||active?.error)&&<div role="alert" className="rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm leading-6 text-red-200">{error||api.error||active?.error}</div>}
   {!defaults?<p className="text-sm text-slate-500">백엔드에서 공식 예제 설정을 읽는 중입니다.</p>:<>
   <div><h3 className="text-xl font-bold">{step==='data'?'시장 데이터 준비':step==='train'?'강화학습 모델 선택·학습':'모델·기준 전략 백테스트'}</h3><p className="mt-2 text-xs text-blue-600">{step==='data'?'YahooDownloader · FeatureEngineer · data_split':step==='train'?'StockTradingEnv · DRLAgent · 모델별 실제 학습 상태':'DRL Agents · MVO · DJIA'}</p></div>
   {step==='data'&&<>
    <div className="grid gap-3 sm:grid-cols-3">{metric('종목 그룹',defaults.ticker_group)}{metric('기술지표',defaults.indicators.length)}{metric('시장 위험 변수','VIX · Turbulence')}</div>
    <div className="grid items-start gap-4 lg:grid-cols-2">
     <section className={panel}><h4 className="mb-5 font-semibold">데이터 설정</h4><p className="text-xs text-slate-500">데이터 공급원</p><div className={input}>{defaults.data_source}</div><label className="mt-4 block text-xs text-slate-500">종목 목록<textarea aria-label="Yahoo 종목 목록" rows={3} className={input} value={value('tickers')} onChange={e=>change('tickers',e.target.value)}/></label>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">{([{key:'train_start',name:'학습 시작일'},{key:'train_end',name:'학습 종료일 · 미포함'},{key:'trade_start',name:'백테스트 시작일'},{key:'trade_end',name:'백테스트 종료일 · 미포함'}]).map(field=><label key={field.key} className="text-xs text-slate-500">{field.name}<input aria-label={field.name} type="date" className={input} value={value(field.key)} onChange={e=>change(field.key,e.target.value)}/></label>)}</div>
      <div className="mt-6 flex flex-wrap gap-3"><button className={button} disabled={busy||pending.has('framework/stock_data')} onClick={()=>void start('data')}><Play size={14}/>데이터 준비</button><button className={button+' !bg-slate-700'} onClick={()=>{if(onStageChange)onStageChange('train');else location.hash='stock-training'}}>다음 단계<ArrowRight size={14}/></button></div>
     </section>
     <section className={panel}><h4 className="mb-4 font-semibold">데이터 처리 과정</h4>{[['OHLCV 수집','YahooDownloader'],['기술지표',defaults.indicators.join(' · ')],['위험 지표','VIX · Turbulence'],['학습 데이터',dataset?display(dataset.value?.train_rows)+'행':'실행 전'],['백테스트 데이터',dataset?display(dataset.value?.trade_rows)+'행':'실행 전']].map(([name,text])=><div key={name} className="flex justify-between gap-5 border-b border-slate-200 py-4 text-xs"><span className="shrink-0">{name}</span><span className="text-right text-blue-600">{text}</span></div>)}<h5 className="my-4 text-sm font-medium">결과 파일</h5>{files(dataset)}</section>
    </div>
   </>}
   {step==='train'&&<>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{metric('선택 모델',models.length)}{metric('모델별 학습 단계',Number(value('total_timesteps')))}{metric('초기 자산',Number(value('initial_amount')))}{metric('거래 비용',value('cost_pct')+'%')}</div>
    <div className="grid items-start gap-4 lg:grid-cols-2">
     <section className={panel}><h4 className="mb-4 font-semibold">학습 모델 선택</h4><div className="grid gap-3 sm:grid-cols-2">{defaults.algorithms.map(name=><label key={name} className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-3 text-sm"><input type="checkbox" checked={models.includes(name)} disabled={busy} onChange={()=>setSelection(old=>{const list=old??defaults.algorithms;return list.includes(name)?list.filter(v=>v!==name):[...list,name]})}/>{name.toUpperCase()}</label>)}</div>
      <label className="mt-5 block text-xs text-slate-500">준비된 데이터<select className={input} aria-label="FinRL 학습 데이터" value={dataset?.job_id??''} onChange={e=>setDataId(e.target.value)}><option value="">데이터 준비가 필요합니다.</option>{runs?.stock_data.filter(r=>r.status==='complete').map(r=><option key={r.job_id} value={r.job_id}>{r.job_id.slice(0,8)} · {r.value?.stock_dimension}종목 · {r.value?.train_rows}행</option>)}</select></label>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">{[{key:'total_timesteps',name:'학습 단계 · 각 모델'},{key:'initial_amount',name:'초기 자산'},{key:'cost_pct',name:'매수·매도 비용 (%)'}].map(field=><label key={field.key} className="text-xs text-slate-500">{field.name}<input type="number" aria-label={field.name} className={input} value={value(field.key)} onChange={e=>change(field.key,e.target.value)}/></label>)}</div>
      <details className="mt-5 text-xs"><summary className="cursor-pointer text-blue-600">공식 예제의 모델별 기본 설정</summary><pre className="mt-3 overflow-auto rounded-lg bg-slate-50 p-3 leading-6">{JSON.stringify(Object.fromEntries(models.map(name=>[name,defaults.model_kwargs[name]])),null,2)}</pre></details>
      <button className={button+' mt-6'} disabled={busy||dataset?.status!=='complete'||!models.length||pending.has('framework/stock_train')} onClick={()=>void start('train')}><Play size={14}/>선택한 모델 학습 시작</button>
     </section>
     <section className={panel}><h4 className="mb-4 font-semibold">모델 학습 상태</h4>{defaults.algorithms.map(name=>{const row=training?.model_states?.[name];return <div key={name} className="border-b border-slate-200 py-4"><div className="flex justify-between gap-3 text-sm"><b>{name.toUpperCase()}</b><span className="text-blue-600">{row?statusLabel[row.status]??row.status:'학습 기록 없음'}</span></div>{row?.num_timesteps!=null&&<p className="mt-2 text-xs text-slate-500">저장된 학습 단계 {display(row.num_timesteps)}</p>}{row?.error&&<p className="mt-2 text-xs text-red-300">{row.error}</p>}</div>})}<h5 className="my-4 text-sm font-medium">저장 모델</h5>{files(training)}<button className={button+' mt-5 !bg-slate-700'} onClick={()=>{if(onStageChange)onStageChange('backtest');else location.hash='backtest'}}>백테스트 화면<ArrowRight size={14}/></button></section>
    </div>
   </>}
   {step==='backtest'&&<>
    <div className="grid items-start gap-4 lg:grid-cols-2">
     <section className={panel}><h4 className="mb-4 font-semibold">평가할 학습 결과</h4><select className={input} aria-label="FinRL 백테스트 정책" value={training?.job_id??''} onChange={e=>{setTrainingId(e.target.value);setBacktestSelection(null)}}><option value="">완료된 학습 결과가 필요합니다.</option>{runs?.stock_train.filter(r=>r.status==='complete').map(r=><option key={r.job_id} value={r.job_id}>{r.job_id.slice(0,8)} · {Object.keys(r.model_states??{}).map(name=>name.toUpperCase()).join(' / ')}</option>)}</select><div className="mt-4 flex flex-wrap gap-3">{available.map(name=><label key={name} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={comparisons.includes(name)} onChange={()=>setBacktestSelection(old=>{const list=old??available;return list.includes(name)?list.filter(v=>v!==name):[...list,name]})}/>{name.toUpperCase()}</label>)}</div>
      <div className="mt-5 space-y-3 border-t border-slate-200 pt-4 text-xs"><p>비교 기준 · MVO (평균 분산 최적화)</p><p>시장 지수 · DJIA (^DJI)</p><p className="text-slate-500">초기 자산 {display(training?.settings?.initial_amount)} · 매수·매도 비용 {training?.settings?.cost_pct!=null?Number(training.settings.cost_pct)*100+'%':'—'}</p></div><button className={button+' mt-6'} disabled={busy||training?.status!=='complete'||!comparisons.length||pending.has('framework/stock_backtest')} onClick={()=>void start('backtest')}><Play size={14}/>백테스트 실행</button>
     </section>
     <section className={panel}><h4 className="mb-4 font-semibold">결과 파일</h4>{files(backtest)}{backtest?.value?.total_rows!=null&&<p className="mt-4 text-xs text-slate-500">실제 결과 {backtest.value.total_rows}행</p>}</section>
    </div>
    <section className={panel}><h4 className="mb-4 font-semibold">Portfolio Value Over Time</h4>{backtest?.status==='complete'&&backtest.artifacts.some(file=>file.name==='backtest_result.png')?<img className="w-full rounded-lg" alt="실제 DRL 모델·MVO·DJIA 포트폴리오 가치 비교" src={backtest.artifacts.find(file=>file.name==='backtest_result.png')?.url}/>:<p className="py-2 text-center text-sm text-slate-500">아직 백테스트 그래프가 생성되지 않았습니다.</p>}</section>
    {backtest?.status==='complete'&&backtest.value?.columns&&backtest.value.rows&&<section className={panel+' overflow-x-auto'}><h4 className="mb-4 font-semibold">실제 백테스트 결과 · 최근 20행</h4><table className="w-full whitespace-nowrap text-right text-xs"><thead><tr>{backtest.value.columns.map(name=><th key={name} className="border-b border-slate-200 px-3 py-3">{name}</th>)}</tr></thead><tbody>{backtest.value.rows.slice(-20).map((row,index)=><tr key={index}>{backtest.value?.columns?.map(name=><td key={name} className="border-b border-slate-800 px-3 py-2">{display(row[name])}</td>)}</tr>)}</tbody></table></section>}
   </>}
   <footer className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4"><div><p className="text-xs text-blue-600">실행 상태 · {stockJob&&busy?'실행 중':active?statusLabel[active.status]??active.status:'미실행'}</p>{script&&<a href={script.url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-xs text-slate-500 hover:text-blue-600">원본 · examples/{script.name}</a>}</div></footer>
   {step==='data'&&<details className={panel}><summary className="cursor-pointer text-sm font-semibold">시세·보조 데이터</summary><div className="mt-5"><MarketScanner/></div></details>}
   {stockJob&&job&&<section className={panel}><div className="mb-3 flex justify-between gap-3 text-sm"><h4 className="font-semibold">실제 백엔드 실행 로그</h4><span className="text-blue-600">{statusLabel[job.status??'']??job.status??'대기'}</span></div><pre className="max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-950 p-4 text-xs leading-6 text-slate-300">{job.log_text||'작업 프로세스의 출력을 기다리는 중입니다.'}</pre></section>}
   </>}
  </div>
 </div>;
}
