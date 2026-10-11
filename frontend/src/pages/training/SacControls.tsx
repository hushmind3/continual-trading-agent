import {useMemo,useState} from 'react';
import {Play,CheckCircle2} from 'lucide-react';
import {useSystemState,useOperations} from '../../data/Operations';
import type {Currency,Instrument,Preflight} from '../../data/types';
import {Button,ErrorMessage,inputClass} from '../../ui/Primitives';
import {Panel,KeyValues} from '../../ui/Panel';
import {DataTable,type Column} from '../../ui/DataTable';
import {number} from '../../ui/format';
interface ChampionOption {name:string;path:string;trained:boolean;parameters:Record<string,number>;identity:{currency:Currency;symbols:string[]}}
interface AlgorithmOption {name:string;parameters:Record<string,string|number|boolean>;steps_per_run:number;uses_replay:boolean}
export function SacControls(){const {state:s,execute,pending}=useOperations();
 const algorithms=useSystemState<{default:string;items:AlgorithmOption[]}>('algorithms');
 const [algorithmChoice,setAlgorithmChoice]=useState(''),[timesteps,setTimesteps]=useState('');
 const [currency,setCurrency]=useState<Currency>(()=>sessionStorage.getItem('training_currency')==='KRW'?'KRW':'USD');
 const [symbols,setSymbols]=useState<string[]>(()=>{try{return JSON.parse(sessionStorage.getItem('training_symbols')||'[]')}catch{return []}});
 const [resume,setResume]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[check,setCheck]=useState<{signature:string;result:Preflight}|null>(null);
 const championOptions=useSystemState<{items:ChampionOption[]}>('champions'),champions=championOptions.data?.items??[];const [champion,setChampion]=useState('');
 const columns=useMemo<Column<Instrument>[]>(()=>[
 {key:'symbol',label:'종목',render:r=>r.symbol,sort:r=>r.symbol},{key:'name',label:'이름',render:r=>r.name},
 {key:'rows',label:'가격 행',render:r=>number(r.rows,0),sort:r=>r.rows},{key:'observations',label:'고유 관측',render:r=>number(r.observations,0)},
 {key:'start',label:'시작',render:r=>r.start?.slice(0,10)||'없음'},{key:'end',label:'종료',render:r=>r.end?.slice(0,10)||'없음'},
 ],[]);
 if(!s)return null;const algorithm=algorithmChoice||algorithms.data?.default||'',official=algorithms.data?.items.find(item=>item.name===algorithm);
 const model=s.models_by_currency?.[currency]??s.model;const body={currency,symbols:[...symbols].sort(),resume,algorithm,...(timesteps?{total_timesteps:Number(timesteps)}:{}),...(champion?{champion_path:champion}:{})},signature=JSON.stringify(body);
 const valid=check?.signature===signature&&check.result.ok;
 const act=async(path:string)=>{setError('');setMessage('');try{if(path==='preflight/train'){const result=await execute<Preflight>(path,body);setCheck({signature,result})}else{const result=await execute<{message:string}>(path,body);setMessage(result.message);setCheck(null)}}catch(e){setError(e instanceof Error?e.message:'요청 실패')}};
 return <Panel title="FinRL · SB3 공식 학습" description="백엔드의 FinRL 알고리즘을 선택하고 공식 DRLAgent로 학습합니다.">
 <ErrorMessage message={algorithms.error}/>
 <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
 <label className="text-xs text-slate-500">알고리즘<select aria-label="FinRL 학습 알고리즘" className={inputClass+' mt-2'} value={algorithm} disabled={s.job.running||!algorithms.data} onChange={e=>{setAlgorithmChoice(e.target.value);setResume(false);setChampion('');setTimesteps('');setCheck(null)}}>{algorithms.data?.items.map(item=><option key={item.name} value={item.name}>{item.name.toUpperCase()}</option>)}</select></label>
 <label className="text-xs text-slate-500">통화<select aria-label="학습 통화" className={inputClass+' mt-2'} value={currency} disabled={s.job.running} onChange={e=>{setCurrency(e.target.value as Currency);setSymbols([]);setCheck(null)}}><option value="USD">USD · 미국 주식 / ETF</option><option value="KRW">KRW · 국내 주식</option></select></label>
 <label className="text-xs text-slate-500">학습 단계<input aria-label="학습 단계" type="number" min={1} className={inputClass+' mt-2'} value={timesteps||official?.steps_per_run||''} disabled={s.job.running} onChange={e=>{setTimesteps(e.target.value);setCheck(null)}}/></label>
 <label className="text-xs text-slate-500">학습 방식<select aria-label="학습 방식" className={inputClass+' mt-2'} value={resume?'resume':'new'} disabled={s.job.running||!!champion} onChange={e=>{setResume(e.target.value==='resume');setCheck(null)}}><option value="new">새 학습</option><option value="resume" disabled={!model.compatible||model.identity.algorithm!==algorithm}>저장 정책 이어 학습</option></select></label>
 </div>
 {algorithm==='sac'&&<label className="mt-4 block text-xs text-slate-500">SAC Champion 선택<select aria-label="SAC Champion 선택" className={inputClass+' mt-2'} value={champion} disabled={s.job.running} onChange={e=>{const path=e.target.value;setChampion(path);setResume(false);const chosen=champions.find(c=>c.path===path);if(chosen){setCurrency(chosen.identity.currency);setSymbols(chosen.identity.symbols)}setCheck(null)}}><option value="">FinRL SAC 정책</option>{champions.map(c=><option key={c.path} value={c.path}>{c.name} · {c.trained?'학습된 상태':'미학습'} · {number(c.parameters?.total_logical_parameters,0)} params</option>)}</select></label>}
 {official&&<details className="my-4 rounded-xl bg-slate-50 p-4"><summary className="cursor-pointer text-xs text-blue-600">{algorithm.toUpperCase()} · FinRL 공식 기본 설정</summary><KeyValues items={Object.entries(official.parameters).map(([key,value])=>[key,String(value)])}/></details>}
 {!model.compatible&&<p className="my-4 rounded-xl bg-amber-50 p-4 text-xs leading-6 text-amber-800">현재 저장본은 최신 학습 환경과 호환되지 않아 이어 학습이 차단되어 있습니다. 아래 호환 사유를 확인하세요.</p>}
 {model.reasons.length>0&&<details className="mb-4 rounded-xl bg-slate-50 p-4 text-xs text-slate-500"><summary className="cursor-pointer font-medium">저장 정책 호환 사유</summary><ul className="mt-3 list-disc space-y-1 pl-4">{model.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul></details>}
 <div className="my-4 flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-slate-500">{symbols.length?symbols.length+'개 선택':'미선택 시 해당 시장의 저장된 등록 종목 전체'}</p><div className="flex gap-2"><Button disabled={s.job.running} onClick={()=>{setSymbols([]);setCheck(null)}}>선택 해제</Button><Button disabled={!model.identity.symbols||model.identity.currency!==currency||s.job.running} onClick={()=>{setSymbols(model.identity.symbols||[]);setCheck(null)}}>저장 정책 종목 선택</Button></div></div>
 <DataTable items={s.data.instruments.filter(r=>r.currency===currency&&r.eligible)} columns={columns} label="학습 종목" keyFor={r=>r.symbol} searchText={r=>r.symbol+' '+r.name} select={{checked:r=>symbols.includes(r.symbol),disabled:r=>!r.stored||s.job.running,toggle:r=>{setSymbols(old=>old.includes(r.symbol)?old.filter(v=>v!==r.symbol):[...old,r.symbol]);setCheck(null)}}}/>
 <div className="my-4 flex flex-wrap gap-3"><Button busy={pending.has('preflight/train')} disabled={s.job.running||!official} onClick={()=>void act('preflight/train')}><CheckCircle2 size={15}/>실행 전 검사</Button><Button tone="primary" busy={pending.has('train')} disabled={!valid||s.job.running||!official} onClick={()=>void act('train')}><Play size={15}/>{algorithm.toUpperCase()} {resume?'이어 학습 시작':'새 학습 시작'}</Button></div>
 {check?.signature===signature&&<div role="status" className={'my-4 rounded-xl p-4 text-xs leading-6 '+(check.result.ok?'bg-emerald-50 text-emerald-800':'bg-amber-50 text-amber-800')}>{check.result.ok?check.result.symbols.length+'개 종목 · 실행 조건 확인됨':check.result.errors.map((r,i)=><p key={i}>{r}</p>)}</div>}
 {check?.result.periods&&<KeyValues items={[['rolling 학습 관측',number(check.result.periods.training_observations,0)],['평가 관측',number(check.result.periods.test_observations,0)]]}/>}
 <ErrorMessage message={error}/>{message&&<p className="text-sm text-emerald-700">{message}</p>}
 <p className="mt-4 text-xs leading-6 text-slate-400">{champion?'선택한 SAC Champion을 새 버전으로 학습합니다.':'학습 결과는 작업별 새 정책으로 저장합니다.'} {number(timesteps?Number(timesteps):official?.steps_per_run,0)}단계 · 정상 종료 시 {official?.uses_replay?'정책과 Replay':'정책'}를 저장합니다.</p>
 </Panel>;
}
