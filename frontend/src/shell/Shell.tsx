import {useCallback,useState,useMemo,Suspense,type ReactNode} from 'react';
import {Activity,Bell,Menu,PanelLeftClose,RefreshCw} from 'lucide-react';
import {useOperations,useSystemState} from '../data/Operations';
import {Drawer,Empty,ErrorMessage,Status} from '../ui/Primitives';
import {CollapsiblePanels} from '../ui/Panel';
import {date} from '../ui/format';
import '../ui/Workspace.css';
import type {BackendMenuCatalog} from '../data/menu_types';
function useNavigation(){
 const catalog=useSystemState<BackendMenuCatalog>('menu_catalog');
 return useMemo(()=>registeredNavigation(catalog.data?.actions??[]),[catalog.data]);
}
import {navigation,registeredNavigation} from './menu_groups/menu_registry';
export {navigation} from './menu_groups/menu_registry';
function destination(hash:string,items=navigation){
 const [name,query='']=hash.replace(/^#/,'').split('?'),params=new URLSearchParams(query);
 let selected=name;
 if(name==='workspace')selected=params.get('tab')==='train'?'learning':'control';
 if(name==='settings')selected=params.get('tab')==='modules'?'frameworks':params.get('tab')==='diagnostics'?'system':'connection';
 return items.find(item=>item.hash===selected)||items[0];
}
export function route(hash:string){const name=hash.replace(/^#/,'').split('?')[0];return name.startsWith('feature-')||name==='backend-browser'?name:destination(hash).hash;}
function errorSection(name:string){
 if(name==='rea'||name==='view:rea'||name.includes('rea.'))return {group:'REA 역공학',target:'rea'};
 if(name.includes('FinRL-X:')||name.includes('stockrl.finrl_trading.'))return {group:'금융',target:'system'};
 if(name.includes('FinRL:')||name.includes('stockrl.finrl.')||['model','models_by_currency','checkpoints'].includes(name))return {group:'금융',target:'frameworks'};
 if(['experts','library','models'].includes(name)||name.startsWith('champion:')||name==='view:champions'||name.includes('platform.expert_')||name.includes('platform.assets')||name.includes('platform.sac_champion'))return {group:'금융',target:'moe'};
 if(name==='data')return {group:'금융',target:'control'};
 if(name==='operations'||name.includes('stockrl.trading.control.'))return {group:'금융',target:'control'};
 return {group:'금융',target:'system'};
}
export function Page({active}:{active:string}){
 const {state}=useOperations(),items=useNavigation(),page=destination(location.hash,items),Component=page.component;
 const missing=state?page.required.filter(key=>state[key as keyof typeof state]==null):[];
 return <>{missing.length?<ErrorMessage message={missing.map(key=>key+': '+(state?.module_errors?.[key]||'상태 조회 실패')).join(' · ')}/>:<Suspense fallback={<p className="text-xs text-slate-500">화면을 여는 중입니다.</p>}><Component key={active}/></Suspense>}</>;
}
export function Shell({active,children}:{active:string;children:ReactNode}){
 const {state,error,refresh}=useOperations(),[alerts,setAlerts]=useState(false),[compact,setCompact]=useState(false),[closedGroups,setClosedGroups]=useState(new Set<string>()),close=useCallback(()=>setAlerts(false),[]);
 const issues=state?.experts?.items.filter(item=>item.active&&item.inference?.reason)||[],items=useNavigation(),page=items.find(item=>item.hash===active);
 const moduleErrors=Object.entries(state?.module_errors??{}),groupErrors=(group:string)=>moduleErrors.filter(([name])=>errorSection(name).group===group).length;
 const visibleErrors=active==='system'?moduleErrors:moduleErrors.filter(([name])=>errorSection(name).target===active);
 return <div className="min-h-dvh bg-[#f4f6fa] text-slate-900">
 <header className="sticky top-0 z-30 border-b border-slate-200 bg-white"><div className="flex min-h-12 items-center justify-between gap-2 px-3 py-2"><div className="flex items-center gap-2"><button aria-label={compact?'메뉴 펼치기':'메뉴 접기'} aria-expanded={!compact} className="rounded p-1.5 text-slate-500" onClick={()=>setCompact(!compact)}>{compact?<Menu size={17}/>:<PanelLeftClose size={17}/>}</button><a href="#control" className="flex items-center gap-2 text-sm font-bold"><Activity size={17} className="text-blue-600"/>프로젝트 플랫폼</a></div><div className="flex items-center gap-2"><Status tone={error?'bad':state?'good':'idle'}>{error?'연결 오류':state?'서버 연결':'연결 중'}</Status>{state?.job?.running&&<a href="#system" className="text-xs text-blue-600">작업 실행 중</a>}<button aria-label="새로고침" onClick={()=>void refresh()} className="p-1.5 text-slate-500"><RefreshCw size={15}/></button><button aria-label={'알림 '+issues.length+'개'} onClick={()=>setAlerts(true)} className="p-1.5 text-slate-500"><Bell size={15}/></button></div></div></header>
 <div className={'workspace-layout '+(compact?'workspace-layout-compact':'')}>
 <aside className="workspace-sidebar" aria-label="전체 기능 메뉴">{[...new Set(items.map(item=>item.group))].map(group=><details key={group} open={compact||!closedGroups.has(group)} className="workspace-menu-group"><summary className={compact?'sr-only':''} onClick={event=>{event.preventDefault();setClosedGroups(old=>{const next=new Set(old);if(next.has(group))next.delete(group);else next.add(group);return next})}}>{group}{groupErrors(group)>0&&<span className="ml-2 text-rose-700">오류 {groupErrors(group)}</span>}</summary><nav aria-label={group}>{items.filter(item=>item.group===group).map(({hash,name,icon:Icon})=><a key={hash} href={'#'+hash} title={name} aria-current={active===hash?'page':undefined} className="workspace-menu-item"><Icon size={16} className="shrink-0"/><span className={compact?'sr-only':''}>{name}</span></a>)}</nav></details>)}</aside>
 <main className={active==='moe'?'min-w-0 px-4 py-6 sm:px-7 sm:py-8':'workspace-compact min-w-0 px-3 py-3'}><div className="mb-3 flex items-center justify-between gap-2"><div><p className="mb-1 text-xs text-slate-500">{page?.group}</p><h1 className={active==='moe'?'text-xl font-bold':'text-sm font-bold'}>{page?.name}</h1></div>{state&&<time className="text-[11px] text-slate-400">{date(state.updated_at)} 기준</time>}</div><ErrorMessage message={error?'통합 API 연결: '+error:''}/>{moduleErrors.length>visibleErrors.length&&<p className="mb-2 text-xs text-amber-700">다른 기능 오류 {moduleErrors.length-visibleErrors.length}개 · <a className="underline" href="#system">진단에서 전체 확인</a></p>}{visibleErrors.map(([name,detail])=><section key={name} className="mb-2"><div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs"><span>확인 구역: {errorSection(name).group} · {name}</span><a className="text-blue-700" href={'#'+errorSection(name).target}>관련 화면 열기 →</a></div><ErrorMessage message={detail}/></section>)}<CollapsiblePanels.Provider value={active!=='moe'}>{children}</CollapsiblePanels.Provider></main>
 </div><Drawer title="현재 실행 · 알림" open={alerts} onClose={close}>{state?.job?.status&&<p className="mb-3 text-xs">{state.job.command} · {state.job.status} · {state.job.detail||date(state.job.started_at)}</p>}{issues.map(item=><p key={item.id} className="mb-2 text-xs text-amber-700">{item.name}: {item.inference?.reason}</p>)}{!issues.length&&!state?.job?.status&&<Empty title="현재 알림 기록이 없습니다."/>}</Drawer>
 </div>;
}
