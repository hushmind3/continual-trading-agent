import {Package,ExternalLink,RefreshCw,Unplug,Trash2,X,FolderOpen,CheckCircle2,Info} from 'lucide-react';
import {Button,Status} from '@platform/ui/Primitives';
import {stages,working,type Project} from './types';
import {navigation} from '@platform/shell/module_loader';
const kinds:Record<string,string>={powershell:'Windows 설치 프로그램',static:'웹 화면',vite:'웹 앱',fastapi:'기능형 앱','python-cli':'명령형 앱','node-mcp':'에이전트용 도구',builtin:'기본 앱',native:'플랫폼 앱'};
export function ProjectCard({project,busy,act,detail}:{project:Project;busy:boolean;act:(operation:string,project:Project)=>void;detail:(project:Project)=>void}){
 const running=working(project.stage),detached=project.stage==='removed',failed=!!project.connection_error||!!project.error&&project.stage==='ready'||['failed','needs_adapter','cancelled','removal_failed'].includes(project.stage);
 const ready=project.stage==='ready'&&(project.can_open??project.builtin)&&!project.error;
 const canDetach=!!project.active_source&&!detached&&!running;
 const checks=project.verification;
 const status=ready&&project.adapter?.kind==='powershell'?'설치 화면 준비됨':project.connection_pending?'메뉴 분리 중':(project.connection_error||project.error&&project.stage==='ready')?'실행 연결 오류':project.stage==='needs_adapter'?'아직 설치되지 않음':stages[project.stage]||project.stage;
 return <article className="space-y-4 py-5 first:pt-0 last:pb-0"><header className="flex items-start justify-between gap-4"><div className="flex min-w-0 gap-3"><Package size={20} className="mt-1 shrink-0 text-slate-400"/><div className="min-w-0"><h3 className="break-words font-semibold">{project.title}</h3><p className="break-all text-xs text-slate-500">{project.repository}</p></div></div><Status tone={failed?'bad':ready?'good':running?'warn':'idle'}>{status}</Status></header>
 <p className="text-sm leading-6 text-slate-600">{project.detail}</p>
 {project.stage!=='not_app'&&(project.error||project.connection_error)&&<p className="break-words text-sm text-rose-600">{(project.error||project.connection_error||'').split('\n')[0].slice(0,220)}</p>}
 <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-500"><span>{project.stage==='not_app'?'문서·분석 자료':project.builtin?'기본 앱':kinds[project.adapter?.kind||'']||'실행 방식 확인 중'}</span>{checks?.original_ui_rendered&&<span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 size={13}/>원본 화면 확인</span>}{checks?.entry_executed&&<span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 size={13}/>프로그램 실행 확인</span>}{ready&&<span>메뉴 연결 완료</span>}{detached&&project.standalone_path&&<span className="text-emerald-700">독립 실행 준비 완료</span>}</div>
 {project.standalone_path&&detached&&<p className="break-all text-xs text-slate-500">보관 위치 · {project.standalone_path}</p>}
 <div className="flex flex-wrap gap-2">{ready&&<Button tone="primary" onClick={()=>{location.href='/#'+(project.builtin?navigation.find(item=>item.group===project.group_title)?.hash||project.menu:project.menu)}}><ExternalLink size={14}/>{project.adapter?.kind==='powershell'?'설치 화면 열기':'실행'}</Button>}
 {detached?<Button tone="primary" disabled={busy||project.connection_pending} onClick={()=>act('reconnect',project)}><RefreshCw size={14}/>다시 연결</Button>:canDetach&&<Button disabled={busy} title="프로그램·설정·실행 환경을 한 폴더로 준비한 뒤 메뉴에서 분리합니다." onClick={()=>act('detach',project)}><Unplug size={14}/>분리</Button>}
 {(project.active_source||project.source||project.standalone_path)&&<Button variant="ghost" disabled={project.stage==='detaching'} onClick={()=>act('folder/open',project)}><FolderOpen size={14}/>폴더 열기</Button>}
 <Button variant="ghost" onClick={()=>detail(project)}><Info size={14}/>설치 정보</Button>
 {!project.builtin&&project.stage!=='not_app'&&(running&&project.stage!=='detaching'&&project.stage!=='awaiting_activation'?<Button tone="danger" onClick={()=>act('cancel',project)}><X size={14}/>설치 취소</Button>:!running&&<Button variant="ghost" disabled={busy} onClick={()=>act(failed&&!project.active_source?'retry':'install',project)}><RefreshCw size={14}/>{failed?'다시 시도':'업데이트'}</Button>)}
 {!project.builtin&&!running&&<Button tone="danger" variant="ghost" disabled={busy} onClick={()=>act('remove',project)}><Trash2 size={14}/>제거</Button>}
 </div></article>;
}
