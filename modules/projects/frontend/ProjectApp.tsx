import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Input,ErrorMessage} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import type {Project} from './types';
import {ApiControls} from './ApiControls';
import {ProjectTask} from './ProjectTask';
import {AppWorkspace,AppFrame} from '@platform/ui/AppWorkspace';
export function ProjectApp({projectId}:{projectId:string}){
 const [project,setProject]=useState<Project|null>(null),[error,setError]=useState(''),[args,setArgs]=useState(''),[text,setText]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{let active=true;if(sessionStorage.getItem('projects.pending-install')===projectId)sessionStorage.removeItem('projects.pending-install');request<Project>('projects/detail',{id:projectId},'GET').then(value=>{if(active)setProject(value)}).catch(e=>{if(active)setError(String(e))});return()=>{active=false}},[projectId]);
 async function run(){setBusy(true);setError('');try{setText((await request<{text:string}>('projects/run',{id:projectId,arguments:args},'POST',130000)).text)}catch(e){setError(String(e))}finally{setBusy(false)}}
 const web=project&&(['static','vite'].includes(project.adapter?.kind||'')||!!project.adapter?.ui);
 return <AppWorkspace title={project?.title||'프로젝트'} subtitle={project?.repository} actions={<><Button onClick={()=>{location.hash='projects/manage/installed'}}>프로젝트 관리</Button>{web&&<Button onClick={()=>window.open('/assets/projects/'+projectId+'/index.html','_blank','noopener')}>원본 화면 열기</Button>}</>}><ErrorMessage message={error}/>
 {web&&<AppFrame title={project?.title+' 원본 화면'} src={'/assets/projects/'+projectId+'/index.html'}/>}
 {project?.adapter?.kind==='python-cli'&&<div className="min-h-0 flex-1 overflow-auto p-4"><Panel title="프로젝트 실행"><div className="flex gap-2"><Input aria-label="실행 인수" placeholder="실행 옵션이나 파일 경로를 입력하세요. 도움말: --help" value={args} onChange={e=>setArgs(e.target.value)}/><Button tone="primary" busy={busy} onClick={()=>void run()}>실행</Button></div><pre className="mt-4 whitespace-pre-wrap break-words text-sm">{text}</pre></Panel></div>}
 {project?.adapter?.kind==='fastapi'&&!web&&<div className="min-h-0 flex-1 overflow-auto p-4"><Panel title="프로젝트 기능"><ApiControls projectId={projectId}/></Panel></div>}
 {project?.adapter?.kind==='node-mcp'&&<ProjectTask projectId={projectId}/>}
 </AppWorkspace>;
}
