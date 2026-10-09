import {useCallback,useState} from 'react';
import {FolderOpen,Layers3} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {request} from '../data/api';
import type {Expert} from '../data/types';
import {Button,ErrorMessage,Skeleton} from '../ui/Primitives';
import {ControlButton} from '../ui/ControlButton';
import {number,bytes} from '../ui/format';
import {ExpertLibraryPanel} from './model/ExpertLibraryPanel';
import {ExpertInspector} from './model/ExpertInspector';
import {ExpertComparison} from './model/ExpertComparison';
import {ModelGuide} from './model/ModelGuide';
import {ServiceProgress} from '../ui/ServiceProgress';

export function ModelWorkspace(){
 const {state}=useOperations();const [inspect,setInspect]=useState<Expert|null>(null),[error,setError]=useState('');
 const close=useCallback(()=>setInspect(null),[]);
 if(!state)return <Skeleton/>;
 const library=state.library?.catalog;const active=library?.active?.length??state.experts.filter(e=>e.enabled!==false).length;
 const inspectExpert=(id:string)=>{
  const current=state.experts.find(e=>e.id===id);const stored=library?.experts?.[id];
  if(current)setInspect(current);
  else if(stored)setInspect({...stored,frozen:true,status:stored.check.status==='passed'?'ready':'needs_input',...stored.check.metrics});
 };
 return <div className="space-y-6">
  <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl bg-[#202e4a] px-6 py-6 text-white">
   <div><div className="mb-2 flex items-center gap-2 text-xs text-blue-200"><Layers3 size={15}/>지속학습 MoE</div>
    <h2 className="text-2xl font-bold">Expert 슬롯 관리</h2>
    <p className="mt-3 text-sm text-slate-300">운영 구성 {active}개 · 누적 학습 조정 {number(state.learner.optimizer_steps??0,0)}회 · 저장 버전 v{state.current_policy?.version??0}</p>
    <p className="mt-2 text-xs text-slate-400">제외한 슬롯의 학습 연결은 보존합니다. 새 패키지는 실제 입력 검사 후 사용하세요.</p>
    {state.agent.execution==='unified-gpu-moe-v1'&&<div className="mt-3 space-y-1 text-sm text-blue-200"><p>통합 GPU MoE · {String(state.agent.device)} · Champion에 포함된 Expert {state.agent.integrated_expert_ids?.length??0}개</p><p>고정 Expert {number(state.agent.frozen_parameters??0,0)} 파라미터 · {bytes(state.agent.frozen_weight_bytes)}</p><p>중앙 모델 {number(state.agent.central_parameters??state.agent.trainable_parameters??0,0)} 파라미터 · {bytes(state.agent.central_weight_bytes)}</p></div>}
   </div>
   <div className="flex flex-wrap gap-2"><ControlButton name="engine" label="MoE"/>
    <Button onClick={()=>void request('model/open-directory',{}).catch(e=>setError(e.message))}><FolderOpen size={15}/>모델 폴더</Button>
   </div>
  </header>
  <ModelGuide/>
  <section className="grid gap-4 rounded-xl bg-white p-4 sm:grid-cols-2"><div><h3 className="mb-3 text-sm font-semibold">Expert 실제 분석 진행</h3><ServiceProgress role="experts"/></div><div><h3 className="mb-3 text-sm font-semibold">중앙 모델 실제 학습 진행</h3><ServiceProgress role="learner"/></div></section>
  {error&&<ErrorMessage message={error}/>}
  <ExpertLibraryPanel onInspect={inspectExpert}/>
  <ExpertComparison/>
  <ExpertInspector expert={inspect?state.experts.find(e=>e.id===inspect.id)??inspect:null} close={close}/>
 </div>;
}
