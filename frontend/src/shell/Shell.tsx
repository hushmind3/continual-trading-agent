import {useCallback,useState,useMemo,Suspense,type ReactNode} from 'react';
import {Layers,Bell,Menu,PanelLeftClose,RefreshCw,AlertTriangle} from 'lucide-react';
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
 const name=hash.replace(/^#/,'').split('?')[0];
 return items.find(item=>item.hash===name)||items[0];
}
export function route(hash:string){const name=hash.replace(/^#/,'').split('?')[0];return name.startsWith('finance/')&&name.split('/').length>2?name:destination(hash).hash;}
function errorSection(name:string){
 if(name==='rea'||name==='view:rea'||name.includes('rea.'))return {group:'REA 역공학',target:'rea/program_analysis'};
 if(name.includes('stockrl.finrl.price_data.')||name.includes('stockrl.finrl.provider_settings.'))return {group:'금융',target:'finance/connection_settings'};
 if(name.includes('FinRL:')||name.includes('stockrl.finrl.')||['model','models_by_currency','checkpoints'].includes(name))return {group:'금융',target:'finance/policy_learning'};
 if(['experts','library','models'].includes(name)||name.startsWith('champion:')||name==='view:champions'||name.includes('platform.expert_')||name.includes('platform.assets')||name.includes('platform.sac_champion'))return {group:'금융',target:'finance/moe'};
 if(name==='data')return {group:'금융',target:'finance/operation_control'};
 if(name==='operations'||name.includes('stockrl.trading.operation_control.'))return {group:'금융',target:'finance/operation_control'};
 return {group:'금융',target:'finance/connection_settings'};
}
export function Page({active}:{active:string}){
 const {state}=useOperations(),items=useNavigation(),page=destination(location.hash,items),Component=page.component;
 const missing=state?page.required.filter(key=>state[key as keyof typeof state]==null):[];
 return <>{missing.length?<ErrorMessage message={missing.map(key=>key+': '+(state?.module_errors?.[key]||'상태 조회 실패')).join(' · ')}/>:<Suspense fallback={<p className="text-xs text-slate-500">화면을 여는 중입니다.</p>}><Component key={active}/></Suspense>}</>;
}
export function Shell({active,children}:{active:string;children:ReactNode}){
 const {state,error,refresh}=useOperations(),[alerts,setAlerts]=useState(false),[compact,setCompact]=useState(false),[mobileMenu,setMobileMenu]=useState(false),[closedGroups,setClosedGroups]=useState(new Set<string>()),close=useCallback(()=>setAlerts(false),[]);
 const closeMobile=useCallback(()=>setMobileMenu(false),[]);
 const issues=state?.experts?.items.filter(item=>item.active&&item.inference?.reason)||[],items=useNavigation(),page=items.find(item=>item.hash===active);
 const moduleErrors=Object.entries(state?.module_errors??{}),groupErrors=(group:string)=>moduleErrors.filter(([name])=>errorSection(name).group===group).length;
 const visibleErrors=moduleErrors.filter(([name])=>errorSection(name).target===active);
 const menu=(iconsOnly=false)=><>{[...new Set(items.map(item=>item.group))].map(group=><details key={group} open={iconsOnly||!closedGroups.has(group)} className="workspace-menu-group"><summary className={iconsOnly?'sr-only':''} onClick={event=>{event.preventDefault();setClosedGroups(old=>{const next=new Set(old);if(next.has(group))next.delete(group);else next.add(group);return next})}}>{group}{groupErrors(group)>0&&<span className="workspace-menu-error">{groupErrors(group)}</span>}</summary><nav aria-label={group}>{items.filter(item=>item.group===group).map(({hash,name,icon:Icon})=><a key={hash} href={'#'+hash} title={name} onClick={()=>setMobileMenu(false)} aria-current={active===hash?'page':undefined} className="workspace-menu-item"><Icon size={18} className="shrink-0"/><span className={iconsOnly?'sr-only':''}>{name}</span></a>)}</nav></details>)}</>;
 return <div className="workspace-app min-h-dvh text-slate-900">
 <a className="workspace-skip-link" href="#workspace-content" onClick={event=>{event.preventDefault();document.getElementById('workspace-content')?.focus();}}>본문으로 이동</a>
 <header className="workspace-header"><div className="workspace-header-brand"><button aria-label={compact?'메뉴 펼치기':'메뉴 접기'} aria-expanded={!compact} className="workspace-icon-button workspace-desktop-toggle" onClick={()=>setCompact(!compact)}>{compact?<Menu size={19}/>:<PanelLeftClose size={19}/>}</button><button aria-label="메뉴 열기" aria-expanded={mobileMenu} className="workspace-icon-button workspace-mobile-toggle" onClick={()=>setMobileMenu(true)}><Menu size={20}/></button><a href="#finance/operation_control" className="workspace-brand"><span className="workspace-brand-mark"><Layers size={18}/></span>프로젝트 플랫폼</a></div><div className="workspace-header-actions"><Status tone={error?'bad':state?'good':'idle'}>{error?'연결 오류':state?'서버 연결':'연결 중'}</Status>{state?.job?.running&&<a href="#finance/policy_learning" className="workspace-job-link">작업 실행 중</a>}<span className="workspace-header-divider"/><button aria-label="새로고침" title="새로고침" onClick={()=>void refresh()} className="workspace-icon-button"><RefreshCw size={18}/></button><button aria-label={'알림 '+(issues.length+moduleErrors.length)+'개'} title="현재 실행 · 알림" onClick={()=>setAlerts(true)} className="workspace-icon-button workspace-notifications"><Bell size={18}/>{issues.length+moduleErrors.length>0&&<span className="workspace-notification-dot"/>}</button></div></header>
 <div className={'workspace-layout '+(compact?'workspace-layout-compact':'')}>
 <aside className="workspace-sidebar" aria-label="전체 기능 메뉴">{menu(compact)}</aside>
 <main id="workspace-content" tabIndex={-1} className="workspace-content min-w-0"><div className="workspace-page-heading"><div><p className="workspace-breadcrumb">{page?.group}</p><h1>{page?.name}</h1></div>{state&&<time className="workspace-updated">{date(state.updated_at)} <span>업데이트</span></time>}</div><ErrorMessage message={error?'통합 API 연결: '+error:''}/>{moduleErrors.length>visibleErrors.length&&<p className="workspace-other-issues">다른 기능 오류 {moduleErrors.length-visibleErrors.length}개 · <button type="button" onClick={()=>setAlerts(true)}>알림 보기</button></p>}{visibleErrors.map(([name,detail])=><details key={name} className="workspace-error-record"><summary><AlertTriangle size={15}/><span>화면 데이터를 불러오지 못했습니다</span><a href={'#'+errorSection(name).target}>관련 화면 <span aria-hidden="true">↗</span></a></summary><ErrorMessage message={detail}/></details>)}<CollapsiblePanels.Provider value={active!=='finance/moe'}>{children}</CollapsiblePanels.Provider></main>
 </div><Drawer title="메뉴" open={mobileMenu} onClose={closeMobile}><div className="workspace-mobile-menu">{menu()}</div></Drawer><Drawer title="현재 실행 · 알림" open={alerts} onClose={close}>{state?.job?.status&&<p className="mb-3 text-xs">{state.job.command} · {state.job.status} · {state.job.detail||date(state.job.started_at)}</p>}{issues.map(item=><p key={item.id} className="mb-2 text-xs text-amber-700">{item.name}: {item.inference?.reason}</p>)}{moduleErrors.map(([name,detail])=><details className="workspace-error-record" key={name}><summary><AlertTriangle size={15}/><a href={'#'+errorSection(name).target} onClick={close}>관련 화면 보기</a></summary><ErrorMessage message={detail}/></details>)}{!issues.length&&!moduleErrors.length&&!state?.job?.status&&<Empty title="현재 알림 기록이 없습니다."/>}</Drawer>
 </div>;
}
