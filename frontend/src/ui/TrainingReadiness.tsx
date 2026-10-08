import {useOperations} from '../data/Operations';
import {ControlButton} from './ControlButton';
import {Status} from './Primitives';

const names={paper:'가상체결',feed:'시세',engine:'MoE',learning:'학습'};
export function TrainingReadiness({compact=false}:{compact?:boolean}){
 const {state}=useOperations();const value=state?.training;
 if(!value)return <p className="text-xs text-slate-400">학습 상태 갱신 중</p>;
 const tone=value.code==='error'?'bad':value.code==='training'?'good':value.code==='paused'||value.code.endsWith('_off')?'neutral':'warn';
 return <div className={compact?'mt-2 space-y-2':'space-y-3'}>
  <Status tone={tone}>{value.label}</Status>
  <p className={`${compact?'max-w-64 text-xs':'max-w-xl text-sm'} leading-5 text-slate-500`}>{value.detail}</p>
  {!!state?.learner.last_update?.samples&&<p className="text-xs leading-5 text-emerald-700">최근 {state.learner.last_update.samples}개 학습 · 누적 업데이트 {state.learner.optimizer_steps??0}회</p>}
  {value.action&&<ControlButton name={value.action} label={names[value.action]} compact/>}
 </div>;
}
