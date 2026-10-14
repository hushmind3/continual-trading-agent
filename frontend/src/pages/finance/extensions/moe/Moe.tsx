import {ModelFiles} from './ModelFiles';
import {useState} from 'react';
import {FolderOpen,Layers3} from 'lucide-react';
import {useOperations} from '../../../../data/Operations';
import {request} from '../../../../data/api';
import {Button,ErrorMessage,Skeleton} from '../../../../ui/Primitives';
import {ExpertLibraryPanel} from './ExpertLibraryPanel';
import {ModelGuide} from './ModelGuide';

export function Moe(){
 const {state}=useOperations();const [error,setError]=useState(''),[source,setSource]=useState('');
 if(!state)return <Skeleton/>;
 return <div className="space-y-6">
  <header className="flex flex-wrap items-start justify-between gap-4 rounded-xl bg-[#202e4a] px-4 py-3 text-white">
   <div><div className="mb-2 flex items-center gap-2 text-xs text-blue-200"><Layers3 size={15}/>지속학습 MoE</div>
    <h2 className="text-lg font-bold">Expert 슬롯 관리</h2>
    <p className="mt-1 text-xs text-slate-300">등록 모델 {state.experts.items.length}개</p>

   </div>
   <div className="flex flex-wrap gap-2">
    <Button onClick={()=>void request('model/open-directory',{}).catch(e=>setError(e.message))}><FolderOpen size={15}/>모델 폴더</Button>
   </div>
  </header>
  <details className="text-xs text-slate-500"><summary className="cursor-pointer">사용 안내</summary><div className="mt-2"><ModelGuide/></div></details>
  {error&&<ErrorMessage message={error}/>}
  <ExpertLibraryPanel initialSource={source}/><details className="rounded-xl border border-slate-200 bg-white px-4 py-3"><summary className="cursor-pointer text-sm font-semibold text-slate-600">모델 폴더 파일</summary><div className="mt-3"><ModelFiles onPick={setSource}/></div></details>
  <a href="#finance/policy_learning" className="text-xs font-semibold text-blue-600">FinRL 정책 학습 →</a>
 </div>;
}
