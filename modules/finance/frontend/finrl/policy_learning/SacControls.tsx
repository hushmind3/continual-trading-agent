import {useEffect,useState} from 'react';
import {Play,CheckCircle2} from 'lucide-react';
import {useSystemState,useOperations} from '@platform/data/Operations';
import type {Currency,Preflight} from '@platform/data/types';
import {Button,ErrorMessage,inputClass,Select,Input} from '@platform/ui/Primitives';
import {Panel,KeyValues} from '@platform/ui/Panel';
import {number} from '@platform/ui/format';
interface ChampionOption {name:string;path:string;checkpoint:string;trained:boolean;parameters:Record<string,number>;identity:{currency:Currency;algorithm:string;timeframe?:string}}
interface AlgorithmOption {name:string;parameters:Record<string,string|number|boolean>;steps_per_run:number;uses_replay:boolean}
export function SacControls(){const {state:s,execute,pending,algorithm:algorithmChoice,selectAlgorithm:setAlgorithmChoice}=useOperations();
 const algorithms=useSystemState<{default:string;items:AlgorithmOption[]}>('algorithms');
 const [timesteps,setTimesteps]=useState('');
 const [timeframe,setTimeframe]=useState<'1d'|'1m'>('1d');
 const [currency,setCurrency]=useState<Currency>(()=>sessionStorage.getItem('training_currency')==='KRW'?'KRW':'USD');
 useEffect(()=>{sessionStorage.setItem('training_currency',currency)},[currency]);
 const [resume,setResume]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[check,setCheck]=useState<{signature:string;result:Preflight}|null>(null);
 const championOptions=useSystemState<{items:ChampionOption[]}>('champions'),champions=championOptions.data?.items??[];const [champion,setChampion]=useState('');
 if(!s)return null;const algorithm=algorithmChoice||algorithms.data?.default||'',official=algorithms.data?.items.find(item=>item.name===algorithm);
 const model=s.models_by_currency?.[currency]??s.model,selectedChampion=champions.find(item=>item.path===champion);
 const selectedCheckpoint=s.checkpoints.find(item=>item.path===selectedChampion?.checkpoint);
 const identity=(selectedCheckpoint?.identity??(selectedChampion?.identity??model.identity)) as {timeframe?:string;training_input?:{timeframe?:string}},savedTimeframe=identity.timeframe??identity.training_input?.timeframe??'1d';
 const body={currency,resume,algorithm,timeframe:resume?savedTimeframe:timeframe,...(timesteps?{total_timesteps:Number(timesteps)}:{}),...(champion?{champion_path:champion}:{}),...(resume&&selectedChampion?{checkpoint:selectedChampion.checkpoint}:{})},signature=JSON.stringify(body);
 const valid=check?.signature===signature&&check.result.ok;
 const invalidSteps=!!timesteps&&(!Number.isSafeInteger(Number(timesteps))||Number(timesteps)<1);
 const checking=pending.has('preflight/train'),starting=pending.has('train'),locked=s.job.running||checking||starting;
 const act=async(path:string)=>{if(locked||invalidSteps)return;setError('');setMessage('');try{if(path==='preflight/train'){const result=await execute<Preflight>(path,body);setCheck({signature,result})}else{const result=await execute<{message:string}>(path,body);setMessage(result.message);setCheck(null)}}catch(e){setError(e instanceof Error?e.message:'요청 실패')}};
 return <Panel title="학습 설정" description="알고리즘과 입력을 정한 뒤, 실행 조건을 확인하고 학습을 시작합니다." className="policy-training-controls" collapsible={false}>
 <ErrorMessage message={algorithms.error}/>
 <fieldset disabled={locked} className="m-0 min-w-0 border-0 p-0"><legend className="sr-only">학습 입력 설정</legend><div className="policy-training-grid">
 <label className="text-xs text-slate-500">알고리즘<Select aria-label="FinRL 학습 알고리즘" className={inputClass+' mt-2'} value={algorithm} disabled={s.job.running||!algorithms.data} onChange={e=>{setAlgorithmChoice(e.target.value);setResume(false);setChampion('');setTimesteps('');setCheck(null)}}>{!algorithms.data&&<option value="">{algorithms.error?'알고리즘 조회 실패':'알고리즘 불러오는 중'}</option>}{algorithms.data?.items.map(item=><option key={item.name} value={item.name}>{item.name.toUpperCase()}</option>)}</Select></label>
 <label className="text-xs text-slate-500">통화<Select aria-label="학습 통화" className={inputClass+' mt-2'} value={currency} disabled={s.job.running} onChange={e=>{setCurrency(e.target.value as Currency);setChampion('');setResume(false);setCheck(null)}}><option value="USD">USD · 미국 주식 / ETF</option><option value="KRW">KRW · 국내 주식</option></Select></label>
 <label className="text-xs text-slate-500">학습 단계<Input aria-label="학습 단계" type="number" min={1} step={1} inputMode="numeric" aria-invalid={invalidSteps} aria-describedby={invalidSteps?'training-steps-error':undefined} className={inputClass+' mt-2'} value={timesteps||official?.steps_per_run||''} disabled={s.job.running} onChange={e=>{setTimesteps(e.target.value);setCheck(null)}}/></label>
 <label className="text-xs text-slate-500">학습 방식<Select aria-label="학습 방식" className={inputClass+' mt-2'} value={resume?'resume':'new'} disabled={s.job.running||!!champion} onChange={e=>{setResume(e.target.value==='resume');setCheck(null)}}><option value="new">새 학습</option><option value="resume" disabled={!model.compatible||model.identity.algorithm!==algorithm}>저장 정책 이어 학습</option></Select></label>
 </div>
 <label className="mt-4 block text-xs text-slate-500">학습 가격 주기<Select aria-label="학습 가격 주기" className={inputClass+' mt-2'} value={resume?savedTimeframe:timeframe} disabled={s.job.running||resume} onChange={e=>{setTimeframe(e.target.value as '1d'|'1m');setCheck(null)}}><option value="1d">일봉 · 저장 역사 가격</option><option value="1m">1분봉 · 수신 완료 시세</option></Select></label>
 <details className="policy-inline-help"><summary>학습 데이터 안내</summary><p className="mt-2 text-xs leading-6 text-slate-500">1분봉은 시세 수신으로 저장된 완료 봉을 사용합니다. 데이터가 부족하면 실행 전 검사에서 차단합니다. 이어 학습은 저장 정책의 주기를 유지합니다.</p></details>
 <label className="mt-4 block text-xs text-slate-500">학습할 모델<Select aria-label="MoE Champion 선택" className={inputClass+' mt-2'} value={champion} disabled={s.job.running} onChange={e=>{const path=e.target.value;setChampion(path);const chosen=champions.find(c=>c.path===path);setResume(!!chosen?.trained);if(chosen){setCurrency(chosen.identity.currency)}setCheck(null)}}><option value="">FinRL {algorithm.toUpperCase()} 새 정책</option>{champions.filter(c=>c.identity.algorithm===algorithm).map(c=><option key={c.path} value={c.path}>{c.name} · {c.trained?'이어 학습':'미학습'}</option>)}</Select></label>
 {official&&<details className="my-4 rounded-xl bg-slate-50 p-4"><summary className="cursor-pointer text-xs text-blue-600">{algorithm.toUpperCase()} · FinRL 공식 기본 설정</summary><KeyValues items={Object.entries(official.parameters).map(([key,value])=>[key,String(value)])}/></details>}
 {!champion&&!model.compatible&&<p className="my-4 rounded-xl bg-amber-50 p-4 text-xs leading-6 text-amber-800">이 저장 모델은 이어 학습할 수 없습니다. 새 학습을 선택하거나 아래 사유를 확인하세요.</p>}
 {!champion&&model.reasons.length>0&&<details className="mb-4 rounded-xl bg-slate-50 p-4 text-xs text-slate-500"><summary className="cursor-pointer font-medium">저장 정책 호환 사유</summary><ul className="mt-3 list-disc space-y-1 pl-4">{model.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul></details>}
 {resume&&selectedChampion&&<p className="mt-3 text-xs text-blue-700">이어 학습 기준: {selectedChampion.name} · {selectedChampion.checkpoint}. 저장된 가중치와 {official?.uses_replay?'경험 재생 기록을':'학습 단계를'} 이어 사용합니다.</p>}
 </fieldset>{invalidSteps&&<p id="training-steps-error" role="alert" className="my-3 text-sm text-rose-700">학습 단계는 1 이상의 정수로 입력하세요.</p>}
 <div className="policy-training-actions"><p role="status">{checking?'실행 조건 확인 중':starting?'학습 시작 요청 중':s.job.running?'학습 진행 중':valid?'학습 준비 완료':'실행 조건을 먼저 확인하세요.'}</p><div className="flex flex-wrap gap-3"><Button busy={pending.has('preflight/train')} disabled={locked||invalidSteps||!official} onClick={()=>void act('preflight/train')}><span className="policy-action-step" aria-hidden="true">1</span><CheckCircle2 size={15}/>실행 조건 확인</Button><Button tone="primary" busy={pending.has('train')} disabled={!valid||locked||invalidSteps||!official} onClick={()=>void act('train')}><span className="policy-action-step" aria-hidden="true">2</span><Play size={15}/>{resume?'이어 학습 시작':'학습 시작'}</Button></div></div>
 {check?.signature===signature&&<div role="status" className={'my-4 rounded-xl p-4 text-xs leading-6 '+(check.result.ok?'bg-emerald-50 text-emerald-800':'bg-amber-50 text-amber-800')}>{check.result.ok?check.result.symbols.length+'개 종목 · 실행 조건 확인됨':check.result.errors.length?check.result.errors.map((r,i)=><p key={i}>{r}</p>):'실행 조건을 충족하지 못했습니다.'}</div>}
 {check?.signature===signature&&check.result.periods&&<KeyValues items={[['rolling 학습 관측',number(check.result.periods.training_observations,0)]]}/>}
 <ErrorMessage message={error}/>{message&&<p className="text-sm text-emerald-700">{message}</p>}
 <details className="policy-inline-help"><summary>결과 저장 안내</summary> <p className="mt-4 text-xs leading-6 text-slate-400">{champion?'선택한 '+algorithm.toUpperCase()+' MoE Champion을 새 버전으로 학습합니다.':'학습 결과는 작업별 새 정책으로 저장합니다.'} 학습 단계는 {number(timesteps?Number(timesteps):official?.steps_per_run,0)}회입니다. {official?.uses_replay?'정상 종료하면 정책과 경험 재생 기록을 함께 저장합니다.':'정상 종료하면 정책을 저장합니다.'}</p></details>
 </Panel>;
}
