import {useMemo,useState} from 'react';
import {Play,CheckCircle2} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import type {Currency,Instrument,Preflight} from '../../data/types';
import {Button,ErrorMessage,inputClass} from '../../ui/Primitives';
import {Panel,KeyValues} from '../../ui/Panel';
import {DataTable,type Column} from '../../ui/DataTable';
import {number} from '../../ui/format';
export function SacControls(){const {state:s,execute,pending}=useOperations();
 const [currency,setCurrency]=useState<Currency>(()=>sessionStorage.getItem('training_currency')==='KRW'?'KRW':'USD');
 const [symbols,setSymbols]=useState<string[]>(()=>{try{return JSON.parse(sessionStorage.getItem('training_symbols')||'[]')}catch{return []}});
 const [resume,setResume]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[check,setCheck]=useState<{signature:string;result:Preflight}|null>(null);
 const columns=useMemo<Column<Instrument>[]>(()=>[
 {key:'symbol',label:'종목',render:r=>r.symbol,sort:r=>r.symbol},{key:'name',label:'이름',render:r=>r.name},
 {key:'rows',label:'가격 행',render:r=>number(r.rows,0),sort:r=>r.rows},{key:'observations',label:'고유 관측',render:r=>number(r.observations,0)},
 {key:'start',label:'시작',render:r=>r.start?.slice(0,10)||'없음'},{key:'end',label:'종료',render:r=>r.end?.slice(0,10)||'없음'},
 ],[]);
 if(!s)return null;const body={currency,symbols:[...symbols].sort(),resume},signature=JSON.stringify(body);
 const valid=check?.signature===signature&&check.result.ok;
 const act=async(path:string)=>{setError('');setMessage('');try{if(path==='preflight/train'){const result=await execute<Preflight>(path,body);setCheck({signature,result})}else{const result=await execute<{message:string}>(path,body);setMessage(result.message);setCheck(null)}}catch(e){setError(e instanceof Error?e.message:'요청 실패')}};
 return <Panel title="공식 SAC 실행" description="현재 데이터와 정책 조건을 검사한 뒤 기존 학습 함수를 호출합니다.">
 <div className="grid gap-4 sm:grid-cols-2"><label className="text-xs text-slate-500">통화<select aria-label="학습 통화" className={inputClass+' mt-2'} value={currency} disabled={s.job.running} onChange={e=>{setCurrency(e.target.value as Currency);setSymbols([]);setCheck(null)}}><option value="USD">USD · 미국 주식 / ETF</option><option value="KRW">KRW · 국내 주식</option></select></label><label className="text-xs text-slate-500">학습 방식<select aria-label="학습 방식" className={inputClass+' mt-2'} value={resume?'resume':'new'} disabled={s.job.running} onChange={e=>{setResume(e.target.value==='resume');setCheck(null)}}><option value="new">새 학습</option><option value="resume" disabled={!s.model.compatible}>저장 정책 이어 학습</option></select></label></div>
 {!s.model.compatible&&<p className="my-4 rounded-xl bg-amber-50 p-4 text-xs leading-6 text-amber-800">현재 저장본은 최신 학습 환경과 호환되지 않아 이어 학습이 차단되어 있습니다. 아래 호환 사유를 확인하세요.</p>}
 {s.model.reasons.length>0&&<details className="mb-4 rounded-xl bg-slate-50 p-4 text-xs text-slate-500"><summary className="cursor-pointer font-medium">저장 정책 호환 사유</summary><ul className="mt-3 list-disc space-y-1 pl-4">{s.model.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul></details>}
 <div className="my-4 flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-slate-500">{symbols.length?symbols.length+'개 선택':'미선택 시 해당 시장의 저장된 등록 종목 전체'}</p><div className="flex gap-2"><Button disabled={s.job.running} onClick={()=>{setSymbols([]);setCheck(null)}}>선택 해제</Button><Button disabled={!s.model.identity.symbols||s.model.identity.currency!==currency||s.job.running} onClick={()=>{setSymbols(s.model.identity.symbols||[]);setCheck(null)}}>저장 정책 종목 선택</Button></div></div>
 <DataTable items={s.data.instruments.filter(r=>r.currency===currency&&r.eligible)} columns={columns} label="학습 종목" keyFor={r=>r.symbol} searchText={r=>r.symbol+' '+r.name} select={{checked:r=>symbols.includes(r.symbol),disabled:r=>!r.stored||s.job.running,toggle:r=>{setSymbols(old=>old.includes(r.symbol)?old.filter(v=>v!==r.symbol):[...old,r.symbol]);setCheck(null)}}}/>
 <div className="my-4 flex flex-wrap gap-3"><Button busy={pending.has('preflight/train')} disabled={s.job.running} onClick={()=>void act('preflight/train')}><CheckCircle2 size={15}/>실행 전 검사</Button><Button tone="primary" busy={pending.has('train')} disabled={!valid||s.job.running} onClick={()=>void act('train')}><Play size={15}/>{resume?'SAC 이어 학습 시작':'SAC 새 학습 시작'}</Button></div>
 {check?.signature===signature&&<div role="status" className={'my-4 rounded-xl p-4 text-xs leading-6 '+(check.result.ok?'bg-emerald-50 text-emerald-800':'bg-amber-50 text-amber-800')}>{check.result.ok?check.result.symbols.length+'개 종목 · 실행 조건 확인됨':check.result.errors.map((r,i)=><p key={i}>{r}</p>)}</div>}
 {check?.result.periods&&<KeyValues items={[['rolling 학습 관측',number(check.result.periods.training_observations,0)],['평가 관측',number(check.result.periods.test_observations,0)]]}/>}
 <ErrorMessage message={error}/>{message&&<p className="text-sm text-emerald-700">{message}</p>}
 <p className="mt-4 text-xs leading-6 text-slate-400">새 학습은 이전 파일을 보관한 후 새 정책을 생성합니다. 공식 예제 한 번에 {number(s.settings.steps_per_run,0)}단계. 정상 종료 시 정책·Replay를 저장합니다.</p>
 </Panel>;
}
