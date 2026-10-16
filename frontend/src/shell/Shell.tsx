import {useCallback,useState,useMemo,useLayoutEffect,useRef,useEffect,Suspense,type ReactNode} from 'react';
import {Layers,Bell,Menu,PanelLeftClose,RefreshCw,AlertTriangle} from 'lucide-react';
import {useOperations,useSystemState} from '../data/Operations';
import {Button,Drawer,Empty,ErrorMessage,Status} from '../ui/Primitives';
import {CollapsiblePanels} from '../ui/Panel';
import {date} from '../ui/format';
import {NavigationTree} from './navigation/NavigationTree';
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
const jobLabels:Record<string,string>={running:'실행 중',starting:'시작 중',pending:'대기',complete:'완료',completed:'완료',saved:'저장 완료',failed:'실패',error:'오류',canceled:'취소됨',cancelled:'취소됨',stopped:'중지됨',idle:'대기',blocked:'확인 필요',finished:'종료'};
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
 return <>{missing.length?<ErrorMessage message={missing.map(key=>key+': '+(state?.module_errors?.[key]||'상태 조회 실패')).join(' · ')}/>:<Suspense fallback={<p className="text-xs text-slate-500">화면을 여는 중입니다.</p>}><Component key={page.mountKey??active}/></Suspense>}</>;
}
export function Shell({active,children}:{active:string;children:ReactNode}){
 const previousPage=useRef(active);
 useLayoutEffect(()=>{window.scrollTo(0,0);if(previousPage.current===active)return;previousPage.current=active;const frame=requestAnimationFrame(()=>document.getElementById('workspace-content')?.focus({preventScroll:true}));return()=>cancelAnimationFrame(frame)},[active]);
 const {state,error,refresh}=useOperations(),[alerts,setAlerts]=useState(false),[compact,setCompact]=useState(false),[mobileMenu,setMobileMenu]=useState(false),close=useCallback(()=>setAlerts(false),[]);
 const [refreshing,setRefreshing]=useState(false),refreshRequest=useRef(false);
 const retry=async()=>{if(refreshRequest.current)return;refreshRequest.current=true;setRefreshing(true);try{await refresh()}finally{refreshRequest.current=false;setRefreshing(false)}};
 const closeMobile=useCallback(()=>setMobileMenu(false),[]);
 const issues=state?.experts?.items.filter(item=>item.active&&item.inference?.reason)||[],items=useNavigation(),page=items.find(item=>item.hash===active);
 useEffect(()=>{document.title=page?.name?page.name+' · 프로젝트 플랫폼':'프로젝트 플랫폼'},[page?.name]);
 const moduleErrors=Object.entries(state?.module_errors??{}),groupErrors=(group:string)=>moduleErrors.filter(([name])=>errorSection(name).group===group).length;
 const notice=(key:string,title:string,target:string,detail:string)=><article key={key} className="workspace-notice"><header><h3>{title}</h3><a href={'#'+target} onClick={close} aria-label={title+' 화면 열기'}>화면 열기 <span aria-hidden="true">↗</span></a></header><details><summary>오류 상세</summary><ErrorMessage message={detail}/></details></article>;
 const visibleErrors=moduleErrors.filter(([name])=>errorSection(name).target===active);
 const menu=(compact=false)=><NavigationTree items={items} active={active} compact={compact} onNavigate={closeMobile} errorCount={groupErrors}/>;
 return <div className="workspace-app min-h-dvh text-slate-900">
 <a className="workspace-skip-link" href="#workspace-content" onClick={event=>{event.preventDefault();document.getElementById('workspace-content')?.focus();}}>본문으로 이동</a>
 <header className="workspace-header"><div className="workspace-header-brand"><Button aria-label={compact?'메뉴 펼치기':'메뉴 접기'} aria-expanded={!compact} className="workspace-icon-button workspace-desktop-toggle" onClick={()=>setCompact(!compact)}>{compact?<Menu size={19}/>:<PanelLeftClose size={19}/>}</Button><Button aria-label="메뉴 열기" aria-expanded={mobileMenu} className="workspace-icon-button workspace-mobile-toggle" onClick={()=>setMobileMenu(true)}><Menu size={20}/></Button><a href="#finance/operation_control" className="workspace-brand"><span className="workspace-brand-mark"><Layers size={18}/></span>프로젝트 플랫폼</a></div><div className="workspace-header-actions"><Status tone={error?'bad':state?'good':'idle'}>{error?'연결 오류':state?'서버 연결':'연결 중'}</Status>{state?.job?.running&&<a href="#finance/policy_learning" className="workspace-job-link">작업 실행 중</a>}<span className="workspace-header-divider"/><Button aria-label={refreshing?'새로고침 중':'새로고침'} title="새로고침" aria-busy={refreshing} disabled={refreshing} onClick={()=>void retry()} className="workspace-icon-button"><RefreshCw size={18} className={refreshing?'animate-spin':undefined}/></Button><Button aria-label={'알림 '+(issues.length+moduleErrors.length)+'개'} title="현재 실행 · 알림" onClick={()=>setAlerts(true)} className="workspace-icon-button workspace-notifications"><Bell size={18}/>{issues.length+moduleErrors.length>0&&<span className="workspace-notification-dot"/>}</Button></div></header>
 <div className={'workspace-layout '+(compact?'workspace-layout-compact':'')}>
 <aside className="workspace-sidebar" aria-label="전체 기능 메뉴">{menu(compact)}</aside>
 <main id="workspace-content" aria-labelledby="workspace-page-title" tabIndex={-1} className="workspace-content min-w-0"><div className="workspace-page-heading"><div><p className="workspace-breadcrumb">{page?.group}</p><h1 id="workspace-page-title">{page?.name}</h1></div>{state&&<time className="workspace-updated">{date(state.updated_at)} <span>업데이트</span></time>}</div><section role="alert" className="workspace-connection-recovery" hidden={!error}><div><h2>{state?'서버 연결이 끊겼습니다.':'서버에 연결할 수 없습니다.'}</h2><p>{state?'마지막으로 받은 데이터를 표시하고 있습니다. 연결이 복구되면 최신 상태로 갱신됩니다.':'서버가 실행 중인지 확인한 뒤 다시 연결하세요.'}</p><details><summary>오류 상세</summary><p>{error}</p></details></div><Button busy={refreshing} onClick={()=>void retry()}>다시 연결</Button></section>{moduleErrors.length>visibleErrors.length&&<p className="workspace-other-issues">다른 기능 오류 {moduleErrors.length-visibleErrors.length}개 · <Button type="button" onClick={()=>setAlerts(true)}>알림 보기</Button></p>}{visibleErrors.map(([name,detail])=><details key={name} className="workspace-error-record"><summary><AlertTriangle size={15}/><span>화면 데이터를 불러오지 못했습니다</span><a href={'#'+errorSection(name).target}>관련 화면 <span aria-hidden="true">↗</span></a></summary><ErrorMessage message={detail}/></details>)}<CollapsiblePanels.Provider value={active!=='finance/moe'}>{state||!error?children:null}</CollapsiblePanels.Provider></main>
 </div><Drawer title="메뉴" open={mobileMenu} onClose={closeMobile}><div className="workspace-mobile-menu">{menu()}</div></Drawer><Drawer title="현재 실행 · 알림" open={alerts} onClose={close}>{state?.job?.status&&<section className="workspace-notice"><header><h3>최근 작업</h3><Status tone={['failed','error'].includes(state.job.status)?'bad':state.job.running?'good':'idle'}>{state.job.running?'실행 중':jobLabels[state.job.status]??'상태 확인 필요'}</Status></header><p>{date(state.job.finished_at??state.job.started_at)}</p><a href="#finance/policy_learning" onClick={close}>학습 화면 보기 ↗</a><details><summary>작업 상세</summary><p>{state.job.status} · {state.job.command}</p><p>{state.job.detail}</p></details></section>}{issues.map(item=>notice('expert:'+item.id,(item.name||item.id)+' 확인 필요','finance/moe',item.inference?.reason??''))}{moduleErrors.map(([name,detail])=>{const target=errorSection(name).target,label=items.find(item=>item.hash===target)?.name??'연결 · 설정';return notice('module:'+name,label+' 확인 필요',target,name+' · '+detail)})}{!issues.length&&!moduleErrors.length&&!state?.job?.status&&<Empty title="현재 알림 기록이 없습니다."/>}</Drawer>
 </div>;
}
