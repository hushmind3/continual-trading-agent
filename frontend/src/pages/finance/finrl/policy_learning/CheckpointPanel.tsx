import {useState} from 'react';
import {apiUrl} from '../../../../data/api';
import {useSystemState,useOperations} from '../../../../data/Operations';
import {Panel,KeyValues} from '../../../../ui/Panel';
import {Button,Empty,ErrorMessage,Status,inputClass} from '../../../../ui/Primitives';
import {bytes,date,number} from '../../../../ui/format';
import {ChampionSpec} from '../../../../ui/ChampionSpec';
import type {Champion} from '../../../../data/library';
export function CheckpointPanel(){
 const {state:s,execute,pending}=useOperations(),champions=useSystemState<{items:Champion[]}>('champions');
 const [path,setPath]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('');
 if(!s)return null;
 const recent=[...s.checkpoints].sort((a,b)=>String(b.file.modified??'').localeCompare(String(a.file.modified??'')));
 const chosen=s.checkpoints.find(item=>item.path===path)??recent[0],model=champions.data?.items.find(item=>item.checkpoint===chosen?.path);
 const input=chosen?.identity.training_input as {consumed_end?:string;end?:string;transitions?:number;elapsed_seconds?:number}|undefined;
 const evaluation=chosen?.evaluation;
 const timestamp=(value:string|undefined)=>value?value.replace('T',' ').slice(0,19):'기록 없음';
 const score=(value:number|undefined)=>value==null?'미평가':number(value,2)+'%';
 const loaded=chosen?Object.values(s.operations?.policies??{}).find(item=>item.path===chosen.path):undefined;
 const load=async()=>{if(!chosen)return;setError('');setMessage('');try{await execute('checkpoints/restore',{path:chosen.path});setMessage('모델을 메모리에 로드했습니다.')}catch(e){setError(e instanceof Error?e.message:'모델 로딩 실패')}};
 return <Panel title="저장 모델 · 실제 학습 결과" description="저장된 결과를 먼저 확인하세요. 모델 로드를 눌러야 운영에 사용하는 정책이 바뀝니다.">
 <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{recent.slice(0,4).map(item=>{
 const used=Object.values(s.operations?.policies??{}).some(policy=>policy.path===item.path);
 return <button key={item.path} type="button" aria-pressed={chosen?.path===item.path} onClick={()=>{setPath(item.path);setMessage('');setError('')}} className={'rounded-xl border p-4 text-left '+(chosen?.path===item.path?'border-blue-500 bg-blue-50':'border-slate-200 bg-white')}>
 <p className="text-xs text-slate-500">{String(item.identity.currency??'통화 미기록')} · {String(item.identity.timeframe??'주기 미기록')} · {used?'운영 선택됨':'저장된 후보'}</p>
 <p className="mt-1 break-all text-sm font-semibold">{item.name}</p>
 <p className="mt-2 text-sm">{number(item.num_timesteps,0)} 학습 단계 · {number(item.updates,0)} 업데이트</p>
 <p className="mt-1 text-xs text-slate-500">{item.evaluation?'가상원장 비교 평가 있음':'비교 평가 기록 없음'}</p>
 </button>})}</div>
 {s.checkpoints.length?<><div className="flex flex-wrap items-center gap-2"><select aria-label="저장 모델 선택" className={inputClass+' min-w-0 flex-1'} value={chosen?.path??''} onChange={e=>{setPath(e.target.value);setMessage('');setError('')}}><option value="">저장 모델 선택</option>{s.checkpoints.map(item=><option key={item.path} value={item.path}>{item.name} · {String(item.identity.algorithm??'').toUpperCase()} · {item.num_timesteps===0?'미학습':number(item.num_timesteps,0)+'단계'}{item.compatible?'':' · 환경 미호환'}</option>)}</select><Button tone="primary" disabled={!chosen||!chosen.compatible||s.job.running} busy={pending.has('checkpoints/restore')} onClick={()=>void load()}>모델 로드</Button>{chosen&&<a className="text-xs font-semibold text-blue-600" href={apiUrl('checkpoint',{path:chosen.path})} download>모델 다운로드</a>}</div>
 {chosen&&<div className="mt-3"><Status tone={loaded?.loaded?'good':chosen.compatible?'idle':'warn'}>{loaded?.loaded?'로드됨 · '+loaded.device:chosen.compatible?'로드 확인 없음':'현재 환경과 미호환'}</Status><KeyValues items={[['모델 파일',chosen.path],['저장 시각',date(chosen.file.modified)],['모델 크기',bytes(chosen.file.bytes)],['학습 알고리즘',String(chosen.identity.algorithm??'').toUpperCase()],['학습 단계',number(chosen.num_timesteps,0)],['가중치 업데이트',number(chosen.updates,0)],['이번 저장에서 학습한 봉',input?.transitions==null?'기록 없음':number(input.transitions,0)],['실제로 학습한 마지막 봉',timestamp(input?.consumed_end)],['입력 데이터의 최신 봉',timestamp(input?.end)]]}/>
 {input?.consumed_end&&input.end&&input.consumed_end<input.end&&<p className="mt-3 text-xs text-amber-700">입력 최신 시각까지 학습한 상태가 아닙니다. 마지막 소비 봉 이후 데이터가 남아 있습니다.</p>}
 {evaluation?<section className="mt-4 rounded-xl border border-slate-200 p-4" aria-label="저장된 비교 평가"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold">같은 과거 구간의 가상원장 비교</h3><Status tone={evaluation.return_difference_percentage_points>0?'good':'warn'}>{evaluation.return_difference_percentage_points>0?'기준보다 높음':evaluation.return_difference_percentage_points<0?'기준보다 낮음':'기준과 동일'}</Status></div>
 <p className="mt-2 text-xs text-slate-500">{timestamp(evaluation.candidate.start)} ~ {timestamp(evaluation.candidate.end)} · {evaluation.currency} · {evaluation.source} · {evaluation.timeframe}</p>
 <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="text-xs text-slate-500"><th className="py-2">정책</th><th>수익률</th><th>최대 낙폭</th></tr></thead><tbody><tr className="border-t"><td className="py-2">기준 · {evaluation.baseline.checkpoint.split(/[\\/]/).at(-2)}</td><td>{score(evaluation.baseline.return_pct)}</td><td>{score(evaluation.baseline.max_drawdown_pct)}</td></tr><tr className="border-t"><td className="py-2">선택 · {chosen.name}</td><td>{score(evaluation.candidate.return_pct)}</td><td>{score(evaluation.candidate.max_drawdown_pct)}</td></tr></tbody></table></div>
 <p className="mt-2 text-sm font-semibold">기준 대비 {number(evaluation.return_difference_percentage_points,2)}%p</p><p className="mt-2 text-xs text-slate-500">저장된 과거 평가입니다. 실거래 수익이나 미래 수익을 보장하지 않으며, 후보 선택만으로 운영 정책이 바뀌지 않습니다.</p></section>:<p className="mt-4 text-xs text-slate-500">이 모델의 유효한 비교 평가 기록이 없습니다. 학습 단계 수만으로 수익 개선을 판단하지 않습니다.</p>}
 {model&&<details className="mt-3"><summary className="cursor-pointer text-xs text-blue-600">모델 세부 구조</summary><div className="mt-3"><ChampionSpec model={model}/></div></details>}</div>}</>:<Empty title="저장된 학습 모델이 없습니다."/>}
 <ErrorMessage message={error}/>{message&&<p className="mt-3 text-xs text-emerald-700">{message}</p>}
 </Panel>;
}
