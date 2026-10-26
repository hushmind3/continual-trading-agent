import {useEffect,useState} from 'react';
import {KeyRound} from 'lucide-react';
import {request} from '@platform/data/api';
import {Status,Empty,Button} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import type {Project} from './types';
import {ProjectCard} from './ProjectCard';
export function InstalledProjects({items,busy,act,detail}:{items:Project[];busy:boolean;act:(operation:string,project:Project)=>void;detail:(project:Project)=>void}){
 const groups=[{title:'설치한 앱',items:items.filter(project=>!project.builtin)},{title:'플랫폼 기본 앱',items:items.filter(project=>project.builtin)}];
 return <div className="space-y-6">{groups.map(group=><Panel key={group.title} title={group.title} actions={<Status>{group.items.length}개</Status>}>{group.items.length?<div className="divide-y divide-slate-100">{group.items.map(project=><ProjectCard key={project.id} project={project} busy={busy} act={act} detail={detail}/>)}</div>:<Empty title="아직 설치한 앱이 없습니다." detail="GitHub 주소나 검색으로 앱을 추가하세요." action={<Button onClick={()=>{location.hash='projects/manage/search'}}>앱 추가</Button>}/>}</Panel>)}</div>;
}

/** App-owned action registered with the shared platform header. */
export function InstalledServiceActions(){
 const [service,setService]=useState<{menu:string}>();
 useEffect(()=>{let live=true;const refresh=()=>{void request<{items:{url:string;menu:string}[]}>('projects/installed',{},'GET').then(result=>{
  const installed=result.items.find(item=>{try{return new URL(item.url).pathname.replace(/(?:\.git)?\/?$/,'').toLowerCase()==='/tashfeenahmed/freellmapi'}catch{return false}});
  if(live)setService(installed?.menu?installed:undefined);
 }).catch(()=>{})};refresh();window.addEventListener('focus',refresh);return()=>{live=false;window.removeEventListener('focus',refresh)}},[]);
 return service?<Button variant="ghost" className="max-sm:px-2" aria-label="무료 모델·계정" title="FreeLLMAPI · 제공업체 계정·연결·자동 라우팅" onClick={()=>{location.hash='#'+service.menu}}><KeyRound size={17}/><span className="hidden sm:inline">무료 모델·계정</span></Button>:null;
}
