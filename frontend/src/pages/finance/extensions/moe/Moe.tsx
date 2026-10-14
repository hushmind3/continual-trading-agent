import {ModelFiles} from './ModelFiles';
import {useState} from 'react';
import {FolderOpen,Layers3} from 'lucide-react';
import {useOperations} from '../../../../data/Operations';
import {request} from '../../../../data/api';
import {Button,ErrorMessage,Skeleton} from '../../../../ui/Primitives';
import {ExpertLibraryPanel} from './ExpertLibraryPanel';
import {ModelGuide} from './ModelGuide';

export function Moe(){
 const {state}=useOperations();const [error,setError]=useState(''),[source,setSource]=useState({path:'',selection:0});
 if(!state)return <Skeleton/>;
 return <div className="expert-workspace space-y-6">
  <header className="expert-workspace-heading">
   <div><div className="expert-workspace-eyebrow"><Layers3 size={16}/>모델 구성</div>
    <h2>Expert 라이브러리</h2>
    <p>등록 항목 {state.experts.items.length}개 · 원본과 정밀도 버전을 함께 관리합니다.</p>

   </div>
   <div className="flex flex-wrap gap-2">
    <Button onClick={()=>void request('model/open-directory',{}).catch(e=>setError(e.message))}><FolderOpen size={15}/>모델 폴더</Button>
   </div>
  </header>
  <details className="expert-help text-xs text-slate-500"><summary className="cursor-pointer">사용 안내</summary><div className="mt-2"><ModelGuide/></div></details>
  {error&&<ErrorMessage message={error}/>}
  <ExpertLibraryPanel initialSource={source.path} sourceSelection={source.selection}/><details className="workspace-disclosure rounded-xl border border-slate-200 bg-white px-4 py-3"><summary className="cursor-pointer text-sm font-semibold text-slate-600">모델 폴더 파일</summary><div className="mt-3"><ModelFiles onPick={path=>setSource(current=>({path,selection:current.selection+1}))}/></div></details>
  <a href="#finance/policy_learning" className="text-xs font-semibold text-blue-600">FinRL 정책 학습 →</a>
 </div>;
}
