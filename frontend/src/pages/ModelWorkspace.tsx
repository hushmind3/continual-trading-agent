import {useState} from 'react';
import {FolderOpen,Layers3} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {request} from '../data/api';
import {Button,ErrorMessage,Skeleton} from '../ui/Primitives';
import {ExpertLibraryPanel} from './model/ExpertLibraryPanel';
import {ModelGuide} from './model/ModelGuide';

export function ModelWorkspace(){
 const {state}=useOperations();const [error,setError]=useState('');
 if(!state)return <Skeleton/>;
 return <div className="space-y-6">
  <header className="flex flex-wrap items-start justify-between gap-4 rounded-2xl bg-[#202e4a] px-6 py-6 text-white">
   <div><div className="mb-2 flex items-center gap-2 text-xs text-blue-200"><Layers3 size={15}/>지속학습 MoE</div>
    <h2 className="text-2xl font-bold">Expert 슬롯 관리</h2>
    <p className="mt-3 text-sm text-slate-300">등록 모델 {state.experts.items.length}개</p>
    <p className="mt-2 text-xs text-slate-400">Frozen Expert를 학습 가능한 MoE 결합부와 SB3 SAC Actor·Twin Critic에 조립해 버전별 Champion을 생성합니다.</p>
   </div>
   <div className="flex flex-wrap gap-2">
    <Button onClick={()=>void request('model/open-directory',{}).catch(e=>setError(e.message))}><FolderOpen size={15}/>모델 폴더</Button>
   </div>
  </header>
  <ModelGuide/>
  {error&&<ErrorMessage message={error}/>}
  <ExpertLibraryPanel/>
 </div>;
}
