import {useCallback,useState} from 'react';
import {FolderOpen,Layers3} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {request} from '../data/api';
import type {Expert} from '../data/types';
import {Button,ErrorMessage,Skeleton} from '../ui/Primitives';
import {ExpertLibraryPanel} from './model/ExpertLibraryPanel';
import {ExpertInspector} from './model/ExpertInspector';
import {ExpertComparison} from './model/ExpertComparison';
import {ModelGuide} from './model/ModelGuide';
import {ServiceProgress} from '../ui/ServiceProgress';

export function ModelWorkspace(){
 const {state}=useOperations();const [inspect,setInspect]=useState<Expert|null>(null),[error,setError]=useState('');
 const close=useCallback(()=>setInspect(null),[]);
 if(!state)return <Skeleton/>;
 const active=state.experts.active.length;
 const inspectExpert=(id:string)=>{
  const current=state.experts.items.find(e=>e.id===id);
  if(current)setInspect(current);
 };
 return <div className="space-y-6">
  <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl bg-[#202e4a] px-6 py-6 text-white">
   <div><div className="mb-2 flex items-center gap-2 text-xs text-blue-200"><Layers3 size={15}/>지속학습 MoE</div>
    <h2 className="text-2xl font-bold">Expert 슬롯 관리</h2>
    <p className="mt-3 text-sm text-slate-300">현재 구성에 선택된 Frozen Expert {active}개 · SAC 정책 {state.model.compatible?'호환':'미생성 또는 비호환'}</p>
    <p className="mt-2 text-xs text-slate-400">이 화면의 Expert는 기존 SAC 관측에 연결되는 고정 모델입니다. 중앙 MoE 학습이나 Expert 학습은 제공하지 않습니다.</p>
   </div>
   <div className="flex flex-wrap gap-2">
    <Button onClick={()=>void request('model/open-directory',{}).catch(e=>setError(e.message))}><FolderOpen size={15}/>모델 폴더</Button>
   </div>
  </header>
  <ModelGuide/>
  <section className="grid gap-4 rounded-xl bg-white p-4 sm:grid-cols-2"><div><h3 className="mb-3 text-sm font-semibold">Expert 실제 분석 진행</h3><ServiceProgress role="experts"/></div><div><h3 className="mb-3 text-sm font-semibold">SAC 학습 진행</h3><ServiceProgress role="learner"/></div></section>
  {error&&<ErrorMessage message={error}/>}
  <ExpertLibraryPanel onInspect={inspectExpert}/>
  <ExpertComparison/>
  <ExpertInspector expert={inspect?state.experts.items.find(e=>e.id===inspect.id)??inspect:null} close={close}/>
 </div>;
}
