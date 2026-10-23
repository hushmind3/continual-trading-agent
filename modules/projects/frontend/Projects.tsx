import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage} from '@platform/ui/Primitives';
import {navigation} from '@platform/shell/module_loader';
import {RepositorySearch} from './RepositorySearch';
import {InstalledProjects} from './InstalledProjects';
import {ProjectSettings} from './ProjectSettings';
import {PackageTransfer} from './PackageTransfer';
import {working,type Project} from './types';
export function Projects(){
 const [items,setItems]=useState<Project[]>([]),[error,setError]=useState(''),[sending,setSending]=useState(false),[selected,setSelected]=useState<Project|null>(null);
 const [allowAgent,setAllowAgent]=useState(false);
 const [connectionError,setConnectionError]=useState(''),[notice,setNotice]=useState('');
 const search=!location.hash.includes('/installed');
 async function refresh(){const result=await request<{items:Project[]}>('projects/installed',{},'GET');setItems(result.items)}
 useEffect(()=>{
  let active=true;let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{
   const result=await request<{items:Project[];active_module_ids?:string[]}>('projects/installed',{},'GET');
   if(active){setItems(result.items);setConnectionError('');
    const removed=sessionStorage.getItem('projects.pending-removal');
    if(removed&&result.active_module_ids&&!result.active_module_ids.includes(removed)){sessionStorage.removeItem('projects.pending-removal');location.reload();return}
    const pending=result.items.find(item=>item.id===sessionStorage.getItem('projects.pending-install'));
    if(pending?.stage==='ready'){sessionStorage.removeItem('projects.pending-install');if(!pending.builtin&&pending.menu){location.hash=pending.menu;location.reload();return}}
    if(pending&&['failed','cancelled','needs_adapter','not_app'].includes(pending.stage))sessionStorage.removeItem('projects.pending-install');
    if(result.items.some(item=>!item.builtin&&item.stage==='ready'&&item.menu&&!navigation.some(menu=>menu.hash===item.menu))){location.reload();return}
   }
  }catch{if(active)setConnectionError('메뉴 적용 중 서버에 다시 연결하고 있습니다. 잠시 뒤 자동으로 갱신합니다.')}if(active)timer=setTimeout(poll,2500)};
  void poll();return()=>{active=false;clearTimeout(timer)};
 },[]);
 const busy=sending||items.some(project=>working(project.stage));
 async function action(operation:string,project:Project|string){setSending(true);setError('');setNotice('');try{
  if(operation==='export'&&typeof project!=='string'){
   const result=await request<{url:string;filename:string}>('projects/export',{id:project.id});
   const link=document.createElement('a');link.href=result.url;link.download=result.filename;document.body.append(link);link.click();link.remove();return;
  }
  const body=typeof project==='string'?{url:project,allow_agent:allowAgent}:operation==='install'?{url:project.url,allow_agent:allowAgent||project.allow_agent===true}:{id:project.id,allow_agent:allowAgent||project.allow_agent===true};
  const result=await request<Project>('projects/'+operation,body);if(operation==='folder/open')return;if(['install','retry','reconnect'].includes(operation))sessionStorage.setItem('projects.pending-install',result.id);if(['remove','detach'].includes(operation)){setSelected(null);if(typeof project!=='string'&&project.module_id)sessionStorage.setItem('projects.pending-removal',project.module_id)}await refresh()
 }catch(e){setError(String(e))}finally{setSending(false)}}
 return <section aria-label="프로젝트 관리" className="mx-auto w-full max-w-screen-xl space-y-6 p-4 sm:p-6"><header className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-500">GitHub에서 앱을 설치하고, 실행·분리·재연결하세요.</p><Button onClick={()=>{location.hash=search?'projects/manage/installed':'projects/manage/search'}}>{search?'설치된 프로젝트':'프로젝트 추가'}</Button><Button variant="ghost" disabled={busy} onClick={()=>void request<{detail:string}>('projects/cleanup',{}).then(result=>setNotice(result.detail)).catch(e=>setError(String(e)))}>잔재 정리</Button></header>
 <ErrorMessage message={error||connectionError}/>{notice&&<p role="status" className="text-sm text-emerald-700">{notice}</p>}{search&&<><RepositorySearch busy={busy} install={url=>void action('install',url)} allowAgent={allowAgent} setAllowAgent={setAllowAgent}/><PackageTransfer busy={busy} onInstalled={project=>{sessionStorage.setItem('projects.pending-install',project.id);void refresh().catch(()=>setConnectionError('메뉴 적용 중 서버에 다시 연결하고 있습니다.'))}}/></>}
 {(!search||items.some(project=>working(project.stage)||['failed','needs_adapter','removal_failed','not_app'].includes(project.stage)))&&<InstalledProjects items={items} busy={busy} act={(op,item)=>void action(op,item)} detail={setSelected}/>}
 {selected&&<ProjectSettings key={selected.id} project={selected} onClose={()=>setSelected(null)} onSaved={()=>void refresh()}/>}
 </section>;
}
