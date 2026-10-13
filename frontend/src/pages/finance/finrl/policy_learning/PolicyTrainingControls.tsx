import {useEffect,useState} from 'react';
import {Play,CheckCircle2} from 'lucide-react';
import {useSystemState,useOperations} from '../../../../data/Operations';
import type {Currency,Preflight} from '../../../../data/types';
import {Button,ErrorMessage,inputClass} from '../../../../ui/Primitives';
import {Panel,KeyValues} from '../../../../ui/Panel';
import {number} from '../../../../ui/format';
interface AlgorithmOption {name:string;parameters:Record<string,unknown>;steps_per_run:number;uses_replay:boolean;sb3_defaults?:Record<string,unknown>;parameter_source?:string}
interface ChampionOption {name:string;path:string;trained:boolean;identity:{currency:Currency;symbols:string[];algorithm:string}}

function CurrencyTraining({currency,official}:{currency:Currency;official?:AlgorithmOption}){
 const {state:s,execute,pending}=useOperations(),options=useSystemState<{items:ChampionOption[]}>('champions');
 const [timesteps,setTimesteps]=useState(''),[resume,setResume]=useState(false),[champion,setChampion]=useState('');
 const [error,setError]=useState(''),[message,setMessage]=useState(''),[check,setCheck]=useState<{signature:string;result:Preflight}|null>(null);
 useEffect(()=>{setResume(false);setChampion('');setTimesteps('');setCheck(null)},[official?.name]);
 if(!s)return null;
 const title=currency==='KRW'?'원화 · KRW':'달러 · USD';
 const symbols=[...new Set(s.data.instruments.filter(item=>item.currency===currency&&item.eligible).map(item=>item.symbol))].sort();
 const model=s.models_by_currency?.[currency]??(s.model.identity.currency===currency?s.model:undefined);
 const body={currency,symbols,algorithm:official?.name??'',resume,...(timesteps?{total_timesteps:Number(timesteps)}:{}),...(champion?{champion_path:champion}:{})};
 const signature=JSON.stringify(body),valid=check?.signature===signature&&check.result.ok;
 const act=async(path:string)=>{setError('');setMessage('');try{if(path==='preflight/train'){const result=await execute<Preflight>(path,body);setCheck({signature,result})}else{const result=await execute<{message:string}>(path,body);setMessage(result.message);setCheck(null)}}catch(e){setError(e instanceof Error?e.message:'요청 실패')}};
 return <Panel title={title+' 정책 학습'} description={'등록된 '+title+' 학습 대상 종목 '+symbols.length+'개를 모두 사용합니다.'}>
  <KeyValues items={[
   ['등록 종목',symbols.length+'개 · 개별 선택 없음'],
   ['저장 정책 알고리즘',String(model?.identity.algorithm??'').toUpperCase()||'저장 정책 없음'],
   ['저장된 학습 단계',number(model?.num_timesteps,0)],['저장된 업데이트',number(model?.updates,0)],
  ]}/>
  <div className="mt-4 grid gap-3 sm:grid-cols-2">
   <label className="text-xs text-slate-500">학습 단계<input aria-label={currency+' 학습 단계'} type="number" min={1} className={inputClass+' mt-2'} value={timesteps||official?.steps_per_run||''} disabled={s.job.running} onChange={e=>{setTimesteps(e.target.value);setCheck(null)}}/></label>
   <label className="text-xs text-slate-500">학습 방식<select aria-label={currency+' 학습 방식'} className={inputClass+' mt-2'} value={resume?'resume':'new'} disabled={s.job.running||!!champion} onChange={e=>{setResume(e.target.value==='resume');setCheck(null)}}><option value="new">새 학습</option><option value="resume" disabled={!model?.compatible||model?.identity.algorithm!==official?.name}>저장 정책 이어 학습</option></select></label>
  </div>
  <label className="mt-4 block text-xs text-slate-500">{title} MoE Champion<select aria-label={currency+' MoE Champion 선택'} className={inputClass+' mt-2'} value={champion} disabled={s.job.running} onChange={e=>{setChampion(e.target.value);setResume(false);setCheck(null)}}><option value="">새 정책</option>{options.data?.items.filter(item=>item.identity.currency===currency&&item.identity.algorithm===official?.name).map(item=><option key={item.path} value={item.path}>{item.name} · {item.trained?'학습됨':'미학습'}</option>)}</select></label>
  {!!model?.reasons?.length&&<details className="mt-4 text-xs text-amber-700"><summary>저장 정책 호환 사유</summary><ul className="mt-2 space-y-1">{model?.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul></details>}
  <div className="my-4 flex flex-wrap gap-3"><Button busy={pending.has('preflight/train')} disabled={s.job.running||!official||!symbols.length} onClick={()=>void act('preflight/train')}><CheckCircle2 size={15}/>{title} 실행 전 검사</Button><Button tone="primary" busy={pending.has('train')} disabled={!valid||s.job.running||!official} onClick={()=>void act('train')}><Play size={15}/>{title} {resume?'이어 학습':'새 학습'} 시작</Button></div>
  {check?.signature===signature&&<div role="status" className={'my-3 rounded-xl p-3 text-xs '+(check.result.ok?'bg-emerald-50 text-emerald-800':'bg-amber-50 text-amber-800')}>{check.result.ok?check.result.symbols.length+'개 종목 · 실행 조건 확인됨':check.result.errors.map((value,index)=><p key={index}>{value}</p>)}</div>}
  <ErrorMessage message={error||options.error}/>{message&&<p className="text-xs text-emerald-700">{message}</p>}
  <p className="mt-3 text-xs text-slate-500">등록 종목의 실제 가격과 저장 정책 호환성은 실행 전 검사로 확인합니다. 학습은 위 버튼을 눌러야 시작합니다.</p>
 </Panel>;
}

export function PolicyTrainingControls(){
 const {state:s,algorithm:choice,selectAlgorithm}=useOperations(),algorithms=useSystemState<{default:string;items:AlgorithmOption[]}>('algorithms');
 const algorithm=algorithms.data?.items.some(item=>item.name===choice)?choice:algorithms.data?.default??'';
 const official=algorithms.data?.items.find(item=>item.name===algorithm);
 return <div className="space-y-4"><Panel title="SB3 알고리즘 · 공식 설정" description="원화와 달러를 함께 사용하며, 공식 FinRL·SB3 설정값은 그대로 유지합니다.">
  <ErrorMessage message={algorithms.error}/><label className="block max-w-sm text-xs text-slate-500">학습 알고리즘<select aria-label="FinRL 학습 알고리즘" className={inputClass+' mt-2'} value={algorithm} disabled={s?.job.running||!algorithms.data} onChange={e=>selectAlgorithm(e.target.value)}>{algorithms.data?.items.map(item=><option key={item.name} value={item.name}>{item.name.toUpperCase()}</option>)}</select></label>
  {official&&<div className="mt-4"><p className="mb-2 text-xs font-semibold">{algorithm.toUpperCase()} · FinRL 공식 설정</p><KeyValues items={Object.entries(official.parameters).map(([key,value])=>[key,typeof value==='string'?value:JSON.stringify(value)])}/><details className="mt-4"><summary className="cursor-pointer text-xs text-blue-600">{algorithm.toUpperCase()} · SB3 생성자 기본값</summary><KeyValues items={Object.entries(official.sb3_defaults??{}).map(([key,value])=>[key,typeof value==='string'?value:JSON.stringify(value)])}/></details><p className="mt-3 break-all text-xs text-slate-500">{official.parameter_source}</p></div>}
 </Panel><div className="grid items-start gap-4 xl:grid-cols-2"><CurrencyTraining currency="KRW" official={official}/><CurrencyTraining currency="USD" official={official}/></div></div>;
}
