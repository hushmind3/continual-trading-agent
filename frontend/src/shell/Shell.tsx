import {useCallback,useState,lazy,Suspense,type ReactNode} from 'react';
import {Activity,Bell,Boxes,ChartNoAxesCombined,Database,GraduationCap,Landmark,Menu,PanelLeftClose,RefreshCw,SlidersHorizontal,Stethoscope,Workflow} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {Drawer,Empty,ErrorMessage,Status} from '../ui/Primitives';
import {CollapsiblePanels} from '../ui/Panel';
import {date} from '../ui/format';
import '../ui/Workspace.css';
const reference=lazy(()=>import('../pages/finrl/ReferenceWorkspace').then(m=>({default:m.ReferenceWorkspace})));
export const navigation=[
 {hash:'markets',name:'시장 · 저장 데이터',group:'거래 운영',icon:Database,component:lazy(()=>import('../pages/markets/MarketScanner').then(m=>({default:m.MarketScanner}))),required:['data']},
 {hash:'control',name:'운영 제어',group:'거래 운영',icon:Activity,component:lazy(()=>import('../pages/operations/OperationsBoard').then(m=>({default:m.OperationsBoard}))),required:['operations','resources','job','capabilities']},
 {hash:'paper',name:'가상계좌 · 주문',group:'거래 운영',icon:Landmark,component:lazy(()=>import('../pages/paper/PaperWorkspace').then(m=>({default:m.PaperWorkspace}))),required:['operations']},
 {hash:'learning',name:'정책 학습',group:'FinRL · 메인',icon:GraduationCap,component:lazy(()=>import('../pages/training/TrainingWorkspace').then(m=>({default:m.TrainingWorkspace}))),required:['settings','model','data','experts','job','checkpoints','resources']},
 {hash:'portfolio',name:'정책 평가 · 백테스트',group:'FinRL · 메인',icon:ChartNoAxesCombined,component:lazy(()=>import('../pages/portfolio/PortfolioWorkspace').then(m=>({default:m.PortfolioWorkspace}))),required:['settings','model','evaluation','job','checkpoints']},
 {hash:'finrl',name:'주식거래 데이터 준비',group:'FinRL · 메인',icon:Database,component:reference,required:['job']},
 {hash:'stock-training',name:'주식거래 알고리즘 학습',group:'FinRL · 메인',icon:GraduationCap,component:reference,required:['job']},
 {hash:'backtest',name:'주식거래 백테스트',group:'FinRL · 메인',icon:ChartNoAxesCombined,component:reference,required:['job']},
 {hash:'frameworks',name:'FinRL 모듈 · 도구',group:'FinRL · 메인',icon:Workflow,component:lazy(()=>import('../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.FinrlToolsWorkspace}))),required:['job']},
 {hash:'finrl-trading',name:'보조 데이터 · 전략 · 도구',group:'FinRL-Trading · 보조',icon:Workflow,component:lazy(()=>import('../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.FinrlTradingWorkspace}))),required:['job']},
 {hash:'moe',name:'MoE',group:'프로젝트 확장',icon:Boxes,component:lazy(()=>import('../pages/model/ModelWorkspace').then(m=>({default:m.ModelWorkspace}))),required:['experts','job','library']},
 {hash:'project-modules',name:'프로젝트 모듈',group:'프로젝트 확장',icon:Workflow,component:lazy(()=>import('../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.ProjectModulesWorkspace}))),required:['job']},
 {hash:'connection',name:'연결 · 설정',group:'연결 · 관리',icon:SlidersHorizontal,component:lazy(()=>import('../pages/settings/ConnectionSettings').then(m=>({default:m.ConnectionSettings}))),required:['settings','data','experts','model']},
 {hash:'system',name:'진단 · 로그 · 코드 적용',group:'연결 · 관리',icon:Stethoscope,component:lazy(()=>import('../pages/system/Diagnostics').then(m=>({default:m.Diagnostics}))),required:['settings','resources','job']}
];
function destination(hash:string){
 const [name,query='']=hash.replace(/^#/,'').split('?'),params=new URLSearchParams(query);
 let selected=name;
 if(name==='workspace')selected=params.get('tab')==='train'?'learning':params.get('tab')==='evaluate'?'portfolio':params.get('tab')==='examples'?(params.get('ref')==='train'?'stock-training':params.get('ref')==='backtest'?'backtest':'finrl'):'markets';
 if(name==='settings')selected=params.get('tab')==='modules'?'frameworks':params.get('tab')==='diagnostics'?'system':'connection';
 return navigation.find(item=>item.hash===selected)||navigation[0];
}
export function route(hash:string){return destination(hash).hash;}
function errorSection(name:string){
 if(name.includes('FinRL-X:')||name.includes('stockrl.finrl_trading.'))return {group:'FinRL-Trading · 보조',target:'finrl-trading'};
 if(name.includes('FinRL:')||name.includes('stockrl.finrl.')||['model','models_by_currency','checkpoints'].includes(name))return {group:'FinRL · 메인',target:'frameworks'};
 if(name==='evaluation')return {group:'FinRL · 메인',target:'portfolio'};
 if(['experts','library','models'].includes(name)||name.includes('platform.expert_')||name.includes('platform.assets')||name.includes('platform.sac_champion'))return {group:'프로젝트 확장',target:'moe'};
 if(name==='data')return {group:'거래 운영',target:'markets'};
 if(name==='operations')return {group:'거래 운영',target:'control'};
 return {group:'연결 · 관리',target:'system'};
}
export function Page({active}:{active:string}){
 const {state}=useOperations(),page=destination(location.hash),Component=page.component;
 const missing=state?page.required.filter(key=>state[key as keyof typeof state]==null):[];
 return <>{missing.length?<ErrorMessage message={missing.map(key=>key+': '+(state?.module_errors?.[key]||'상태 조회 실패')).join(' · ')}/>:<Suspense fallback={<p className="text-xs text-slate-500">화면을 여는 중입니다.</p>}><Component key={['finrl','stock-training','backtest'].includes(active)?'finrl-reference':active}/></Suspense>}</>;
}
export function Shell({active,children}:{active:string;children:ReactNode}){
 const {state,error,refresh}=useOperations(),[alerts,setAlerts]=useState(false),[compact,setCompact]=useState(false),[closedGroups,setClosedGroups]=useState(new Set<string>()),close=useCallback(()=>setAlerts(false),[]);
 const issues=state?.experts?.items.filter(item=>item.active&&item.inference?.reason)||[],page=navigation.find(item=>item.hash===active);
 const moduleErrors=Object.entries(state?.module_errors??{}),groupErrors=(group:string)=>moduleErrors.filter(([name])=>errorSection(name).group===group).length;
 return <div className="min-h-dvh bg-[#f4f6fa] text-slate-900">
 <header className="sticky top-0 z-30 border-b border-slate-200 bg-white"><div className="flex min-h-12 items-center justify-between gap-2 px-3 py-2"><div className="flex items-center gap-2"><button aria-label={compact?'메뉴 펼치기':'메뉴 접기'} aria-expanded={!compact} className="rounded p-1.5 text-slate-500" onClick={()=>setCompact(!compact)}>{compact?<Menu size={17}/>:<PanelLeftClose size={17}/>}</button><a href="#markets" className="flex items-center gap-2 text-sm font-bold"><Activity size={17} className="text-blue-600"/>FinRL <span className="hidden text-[11px] font-normal text-slate-400 sm:inline">SB3 SAC</span></a></div><div className="flex items-center gap-2"><Status tone={error?'bad':state?'good':'idle'}>{error?'연결 오류':state?'서버 연결':'연결 중'}</Status>{state?.job?.running&&<a href="#system" className="text-xs text-blue-600">작업 실행 중</a>}<button aria-label="새로고침" onClick={()=>void refresh()} className="p-1.5 text-slate-500"><RefreshCw size={15}/></button><button aria-label={'알림 '+issues.length+'개'} onClick={()=>setAlerts(true)} className="p-1.5 text-slate-500"><Bell size={15}/></button></div></div></header>
 <div className={'workspace-layout '+(compact?'workspace-layout-compact':'')}>
 <aside className="workspace-sidebar" aria-label="전체 기능 메뉴">{[...new Set(navigation.map(item=>item.group))].map(group=><details key={group} open={compact||!closedGroups.has(group)} className="workspace-menu-group"><summary className={compact?'sr-only':''} onClick={event=>{event.preventDefault();setClosedGroups(old=>{const next=new Set(old);if(next.has(group))next.delete(group);else next.add(group);return next})}}>{group}{groupErrors(group)>0&&<span className="ml-2 text-rose-700">오류 {groupErrors(group)}</span>}</summary><nav aria-label={group}>{navigation.filter(item=>item.group===group).map(({hash,name,icon:Icon})=><a key={hash} href={'#'+hash} title={name} aria-current={active===hash?'page':undefined} className="workspace-menu-item"><Icon size={16} className="shrink-0"/><span className={compact?'sr-only':''}>{name}</span></a>)}</nav></details>)}</aside>
 <main className={active==='moe'?'min-w-0 px-4 py-6 sm:px-7 sm:py-8':'workspace-compact min-w-0 px-3 py-3'}><div className="mb-3 flex items-center justify-between gap-2"><div><p className="mb-1 text-xs text-slate-500">{page?.group}</p><h1 className={active==='moe'?'text-xl font-bold':'text-sm font-bold'}>{page?.name}</h1></div>{state&&<time className="text-[11px] text-slate-400">{date(state.updated_at)} 기준</time>}</div><ErrorMessage message={error?'통합 API 연결: '+error:''}/>{moduleErrors.map(([name,detail])=><section key={name} className="mb-2"><div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs"><span>확인 구역: {errorSection(name).group} · {name}</span><a className="text-blue-700" href={'#'+errorSection(name).target}>관련 화면 열기 →</a></div><ErrorMessage message={detail}/></section>)}<CollapsiblePanels.Provider value={active!=='moe'}>{children}</CollapsiblePanels.Provider></main>
 </div><Drawer title="현재 실행 · 알림" open={alerts} onClose={close}>{state?.job?.status&&<p className="mb-3 text-xs">{state.job.command} · {state.job.status} · {state.job.detail||date(state.job.started_at)}</p>}{issues.map(item=><p key={item.id} className="mb-2 text-xs text-amber-700">{item.name}: {item.inference?.reason}</p>)}{!issues.length&&!state?.job?.status&&<Empty title="현재 알림 기록이 없습니다."/>}</Drawer>
 </div>;
}
