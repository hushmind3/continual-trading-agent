import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage} from '@platform/ui/Primitives';
import type {Project} from './types';
import {ApiControls} from './ApiControls';
import {ProjectTask} from './ProjectTask';
import {Panel} from '@platform/ui/Panel';
import {CliApp,type GeneratedInterface} from './CliApp';
import {InstallerApp} from './InstallerApp';
import {AppWorkspace,AppFrame} from '@platform/ui/AppWorkspace';
import {ProjectHarness} from './ProjectHarness';
import {Workspace as ProjectZeroWorkspace} from './project_zero/Workspace';
export function ProjectApp({projectId}:{projectId:string}){
 const [project,setProject]=useState<Project|null>(null),[error,setError]=useState(''),[generated,setGenerated]=useState<GeneratedInterface|null>(null),[tab,setTab]=useState('primary');
 useEffect(()=>{let active=true;if(sessionStorage.getItem('projects.pending-install')===projectId)sessionStorage.removeItem('projects.pending-install');const refresh=()=>request<Project>('projects/detail',{id:projectId},'GET').then(value=>{if(active)setProject(value)}).catch(e=>{if(active)setError(String(e))});void refresh();const timer=window.setInterval(()=>{if(!document.hidden)void refresh()},10000);window.addEventListener('focus',refresh);return()=>{active=false;clearInterval(timer);window.removeEventListener('focus',refresh)}},[projectId]);
 useEffect(()=>{if(project?.adapter?.kind!=='powershell')return;let live=true;request<GeneratedInterface>('projects/interface',{id:projectId},'GET').then(value=>{if(live)setGenerated(value)}).catch(e=>{if(live)setError(String(e))});return()=>{live=false}},[projectId,project?.adapter?.kind]);
 const web=project&&(['static','vite'].includes(project.adapter?.kind||'')||!!project.adapter?.ui);
 const frame='/assets/projects/'+projectId+'/index.html?v='+encodeURIComponent(project?.install_revision||'');
 const workflow=project?.repository?.toLowerCase()==='hushmind3/project-zero';
 return <AppWorkspace title={project?.title||'프로젝트'} subtitle={project?.repository} actions={<>{project?.harness?.enabled&&<ProjectHarness projectId={projectId}/>}<Button onClick={()=>{location.hash='projects/manage/installed'}}>프로젝트 관리</Button>{web&&<Button onClick={()=>window.open(frame,'_blank','noopener')}>원본 화면 열기</Button>}</>}><ErrorMessage message={error}/>
 {workflow?<ProjectZeroWorkspace key={projectId} projectId={projectId}/>:web&&<AppFrame key={frame} title={project?.title+' 원본 화면'} src={frame}/>}
 {project?.adapter?.kind==='python-cli'&&<CliApp projectId={projectId}/>}
 {project?.adapter?.kind==='fastapi'&&!web&&<div className="min-h-0 flex-1 overflow-auto p-4"><Panel title="프로젝트 기능"><ApiControls projectId={projectId}/></Panel></div>}
 {project?.adapter?.kind==='node-mcp'&&<ProjectTask projectId={projectId}/>}
 {project?.adapter?.kind==='powershell'&&<>{!!generated?.commands.length&&<nav aria-label="프로젝트 화면" className="flex shrink-0 gap-2 border-b border-slate-100 px-4 py-2"><Button variant="ghost" tone={tab==='primary'?'primary':'neutral'} onClick={()=>setTab('primary')}>프로그램 설치</Button><Button variant="ghost" tone={tab==='tools'?'primary':'neutral'} onClick={()=>setTab('tools')}>프로젝트 기능</Button></nav>}{tab==='tools'&&generated?<CliApp projectId={projectId} interface={generated}/>:<InstallerApp projectId={projectId}/>}</>}
 </AppWorkspace>;
}
