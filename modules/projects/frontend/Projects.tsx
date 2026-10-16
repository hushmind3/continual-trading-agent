import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Input,ErrorMessage} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {navigation} from '@platform/shell/module_loader';
import {RepositorySearch} from './RepositorySearch';
import {InstalledProjects} from './InstalledProjects';
import {working,type Project} from './types';
export function Projects(){
 const [items,setItems]=useState<Project[]>([]),[error,setError]=useState(''),[sending,setSending]=useState(false),[selected,setSelected]=useState<Project|null>(null),[envKey,setEnvKey]=useState(''),[envValue,setEnvValue]=useState('');
 const search=!location.hash.includes('/installed');
 async function refresh(){const result=await request<{items:Project[]}>('projects/installed',{},'GET');setItems(result.items)}
 useEffect(()=>{
  let active=true;let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{
   const result=await request<{items:Project[]}>('projects/installed',{},'GET');
   if(active){setItems(result.items);setError('');
    const pending=result.items.find(item=>item.id===sessionStorage.getItem('projects.pending-install'));
    if(pending?.stage==='ready'&&pending.menu){sessionStorage.removeItem('projects.pending-install');location.hash=pending.menu;location.reload();return}
    if(pending&&['failed','cancelled','needs_adapter'].includes(pending.stage))sessionStorage.removeItem('projects.pending-install');
    if(result.items.some(item=>!item.builtin&&item.stage==='ready'&&item.menu&&!navigation.some(menu=>menu.hash===item.menu))){location.reload();return}
   }
  }catch(e){if(active)setError(String(e))}if(active)timer=setTimeout(poll,2500)};
  void poll();return()=>{active=false;clearTimeout(timer)};
 },[]);
 const busy=sending||items.some(project=>working(project.stage));
 async function action(operation:string,project:Project|string){setSending(true);setError('');try{const result=await request<Project>('projects/'+operation,typeof project==='string'?{url:project}:operation==='install'?{url:project.url}:{id:project.id});if(['install','retry'].includes(operation))sessionStorage.setItem('projects.pending-install',result.id);if(operation==='remove')setSelected(null);await refresh()}catch(e){setError(String(e))}finally{setSending(false)}}
 async function detail(project:Project){try{setSelected(await request<Project>('projects/detail',{id:project.id},'GET'))}catch(e){setError(String(e))}}
 async function saveEnvironment(){if(!selected)return;try{setSelected(await request<Project>('projects/settings',{id:selected.id,environment:{[envKey]:envValue}}));setEnvValue('');setEnvKey('');await refresh()}catch(e){setError(String(e))}}
 return <main className="mx-auto w-full max-w-screen-xl space-y-6 p-4 sm:p-6"><header className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-500">검색하고 등록하면 설치와 연결을 플랫폼이 처리합니다.</p><Button onClick={()=>{location.hash=search?'projects/manage/installed':'projects/manage/search'}}>{search?'설치된 프로젝트':'프로젝트 추가'}</Button></header>
 <ErrorMessage message={error}/>{search&&<RepositorySearch busy={busy} install={url=>void action('install',url)}/>}
 {(!search||items.some(project=>working(project.stage)||['failed','needs_adapter'].includes(project.stage)))&&<InstalledProjects items={items} busy={busy} act={(op,item)=>void action(op,item)} detail={item=>void detail(item)}/>}
 {selected&&<Panel title={selected.title+' · 상태와 설정'} actions={<Button onClick={()=>setSelected(null)}>닫기</Button>}><p className="mb-3 text-sm text-slate-600">{selected.detail}</p><ErrorMessage message={selected.error||''}/><p className="mb-3 break-all text-xs text-slate-500">소스: {selected.active_source||selected.source||'다운로드 준비 중'}</p>{selected.agent_session&&<a className="text-sm text-blue-600 underline" href="/#ai_agent/Hermes">Hermes의 자동 변환 작업 보기</a>}
 <h3 className="mb-2 mt-5 text-sm font-semibold">프로젝트 환경 설정</h3><p className="mb-3 text-xs text-slate-500">저장된 항목: {selected.environment_keys?.join(', ')||'없음'} · 값은 다시 표시하지 않습니다.</p><div className="flex flex-col gap-2 sm:flex-row"><Input aria-label="환경 설정 이름" placeholder="예: API_KEY" value={envKey} onChange={e=>setEnvKey(e.target.value)}/><Input aria-label="환경 설정 값" type="password" placeholder="값 입력" value={envValue} onChange={e=>setEnvValue(e.target.value)}/><Button disabled={!envKey||!envValue||busy} onClick={()=>void saveEnvironment()}>저장</Button></div>
 <details className="mt-5"><summary className="cursor-pointer text-sm font-medium">설치 로그</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-4 text-xs leading-6">{selected.log||'아직 설치 로그가 없습니다.'}</pre><Button className="mt-2" onClick={()=>void detail(selected)}>로그 새로고침</Button></details></Panel>}
 </main>;
}
