import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage} from '@platform/ui/Primitives';
import {navigation} from '@platform/shell/module_loader';
import {RepositorySearch} from './RepositorySearch';
import {InstalledProjects} from './InstalledProjects';
import {ProjectSettings} from './ProjectSettings';
import {working,type Project} from './types';
export function Projects(){
 const [items,setItems]=useState<Project[]>([]),[error,setError]=useState(''),[sending,setSending]=useState(false),[selected,setSelected]=useState<Project|null>(null);
 const search=!location.hash.includes('/installed');
 async function refresh(){const result=await request<{items:Project[]}>('projects/installed',{},'GET');setItems(result.items)}
 useEffect(()=>{
  let active=true;let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{
   const result=await request<{items:Project[]}>('projects/installed',{},'GET');
   if(active){setItems(result.items);
    const pending=result.items.find(item=>item.id===sessionStorage.getItem('projects.pending-install'));
    if(pending?.stage==='ready'&&pending.menu){sessionStorage.removeItem('projects.pending-install');location.hash=pending.menu;location.reload();return}
    if(pending&&['failed','cancelled','needs_adapter'].includes(pending.stage))sessionStorage.removeItem('projects.pending-install');
    if(result.items.some(item=>!item.builtin&&item.stage==='ready'&&item.menu&&!navigation.some(menu=>menu.hash===item.menu))){location.reload();return}
   }
  }catch(e){if(active)setError(String(e))}if(active)timer=setTimeout(poll,2500)};
  void poll();return()=>{active=false;clearTimeout(timer)};
 },[]);
 const busy=sending||items.some(project=>working(project.stage));
 async function action(operation:string,project:Project|string){setSending(true);setError('');try{const result=await request<Project>('projects/'+operation,typeof project==='string'?{url:project}:operation==='install'?{url:project.url}:{id:project.id});if(['install','retry','reconnect'].includes(operation))sessionStorage.setItem('projects.pending-install',result.id);if(['remove','detach'].includes(operation))setSelected(null);await refresh()}catch(e){setError(String(e))}finally{setSending(false)}}
 return <main className="mx-auto w-full max-w-screen-xl space-y-6 p-4 sm:p-6"><header className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-500">검색하고 설치하면 다운로드부터 실행 연결까지 이어집니다.</p><Button onClick={()=>{location.hash=search?'projects/manage/installed':'projects/manage/search'}}>{search?'설치된 프로젝트':'프로젝트 추가'}</Button></header>
 <ErrorMessage message={error}/>{search&&<RepositorySearch busy={busy} install={url=>void action('install',url)}/>}
 {(!search||items.some(project=>working(project.stage)||['failed','needs_adapter','removal_failed'].includes(project.stage)))&&<InstalledProjects items={items} busy={busy} act={(op,item)=>void action(op,item)} detail={setSelected}/>}
 {selected&&<ProjectSettings key={selected.id} project={selected} onClose={()=>setSelected(null)} onSaved={()=>void refresh()}/>}
 </main>;
}
