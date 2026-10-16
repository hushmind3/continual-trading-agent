import {Package,ExternalLink,RefreshCw,Unplug,X} from 'lucide-react';
import {Button,Status,Empty} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {stages,working,type Project} from './types';
import {navigation} from '@platform/shell/module_loader';
export function InstalledProjects({items,busy,act,detail}:{items:Project[];busy:boolean;act:(operation:string,project:Project)=>void;detail:(project:Project)=>void}){
 return <Panel title="설치된 프로젝트" actions={<Status>{items.length}개</Status>}>
 {items.length===0?<Empty title="아직 설치한 프로젝트가 없습니다." detail="GitHub 검색이나 주소 등록으로 추가하세요." action={<Button onClick={()=>{location.hash='projects/manage/search'}}>프로젝트 추가</Button>}/>:<div className="divide-y divide-slate-100">{items.map(project=><article key={project.id} className="flex flex-col gap-3 py-5 first:pt-0 last:pb-0"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex min-w-0 items-center gap-3"><Package size={20} className="shrink-0 text-slate-400"/><div className="min-w-0"><h3 className="break-all font-semibold">{project.title}</h3><p className="text-xs text-slate-500">{project.repository}</p></div></div><Status tone={project.stage==='ready'?'good':project.stage==='failed'?'bad':working(project.stage)?'warn':'idle'}>{stages[project.stage]||project.stage}</Status></div>
 <p className="text-sm text-slate-500">{project.detail}</p>{project.error&&<p className="whitespace-pre-wrap break-words text-sm text-rose-600">{project.error.slice(0,600)}</p>}
 <div className="flex flex-wrap items-center gap-2">{(project.can_open||project.builtin)&&project.stage!=='removed'&&<Button tone="primary" disabled={project.stage==='awaiting_activation'} onClick={()=>{location.href='/#'+(project.builtin?navigation.find(item=>item.group===project.group_title)?.hash||project.menu:project.menu||'projects/manage/installed')}}><ExternalLink size={14}/>{project.stage==='ready'?'실행':'이전 설치본 열기'}</Button>}
 {!project.builtin&&<Button onClick={()=>detail(project)}>상태·설정</Button>}
 {!project.builtin&&(working(project.stage)&&project.stage!=='awaiting_activation'?<Button tone="danger" onClick={()=>act('cancel',project)}><X size={14}/>설치 취소</Button>:<Button disabled={busy} onClick={()=>act('install',project)}><RefreshCw size={14}/>{project.stage==='failed'?'다시 시도':project.stage==='removed'?'다시 연결':'업데이트'}</Button>)}
 {!project.builtin&&project.active_source&&project.stage!=='removed'&&!working(project.stage)&&<Button variant="ghost" disabled={busy} onClick={()=>act('remove',project)}><Unplug size={14}/>분리</Button>}
 </div></article>)}</div>}
 </Panel>;
}
