import {useCallback,useState,lazy,Suspense,type ReactNode} from 'react';
import {Activity,Bell,Boxes,Layers3,Settings2,RefreshCw} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {Button,Drawer,Empty,ErrorMessage,Status} from '../ui/Primitives';
import {date} from '../ui/format';
import '../ui/Workspace.css';
export const navigation=[
 {hash:'control',name:'운영',icon:Activity,pages:[{id:'overview',name:'운영 · 가상계좌',component:lazy(()=>import('../pages/OperatingWorkspace').then(m=>({default:m.OperatingWorkspace})))}]},
 {hash:'workspace',name:'작업',icon:Layers3,pages:[
  {id:'data',name:'데이터',component:lazy(()=>import('../pages/MarketScanner').then(m=>({default:m.MarketScanner})))},
  {id:'train',name:'정책 학습',component:lazy(()=>import('../pages/TrainingWorkspace').then(m=>({default:m.TrainingWorkspace})))},
  {id:'evaluate',name:'정책 평가',component:lazy(()=>import('../pages/PortfolioWorkspace').then(m=>({default:m.PortfolioWorkspace})))},
  {id:'examples',name:'공식 원형',component:lazy(()=>import('../pages/ReferenceWorkspace').then(m=>({default:m.ReferenceWorkspace})))}]},
 {hash:'moe',name:'MoE',icon:Boxes,pages:[{id:'models',name:'MoE',component:lazy(()=>import('../pages/ModelWorkspace').then(m=>({default:m.ModelWorkspace})))}]},
 {hash:'settings',name:'설정',icon:Settings2,pages:[
  {id:'connection',name:'연결 · 설정',component:lazy(()=>import('../pages/ConnectionSettings').then(m=>({default:m.ConnectionSettings})))},
  {id:'diagnostics',name:'진단',component:lazy(()=>import('../pages/Diagnostics').then(m=>({default:m.Diagnostics})))},
  {id:'modules',name:'공식 모듈',component:lazy(()=>import('../pages/FrameworkWorkspace').then(m=>({default:m.FrameworkWorkspace})))}]}
];
const aliases:Record<string,[string,string]>={markets:['workspace','data'],learning:['workspace','train'],'stock-training':['workspace','examples'],backtest:['workspace','examples'],portfolio:['workspace','evaluate'],connection:['settings','connection'],system:['settings','diagnostics'],frameworks:['settings','modules'],finrl:['workspace','data']};
function destination(hash:string){
 const [name,query='']=hash.replace(/^#/,'').split('?');
 const alias=aliases[name],group=navigation.find(item=>item.hash===(alias?.[0]||name))||navigation[0];
 const tab=new URLSearchParams(query).get('tab')||alias?.[1]||group.pages[0].id;
 return {group,page:group.pages.find(page=>page.id===tab)||group.pages[0]};
}
export function route(hash:string){return destination(hash).group.hash;}
export function Page({active}:{active:string}){
 const {state}=useOperations(),{group,page}=destination(location.hash);
 const required:Record<string,string[]>={control:['model','data','resources','operations','checkpoints','job','capabilities'],moe:['experts','job','library'],workspace:['settings','model','experts','job','checkpoints','data','resources','evaluation','capabilities'],settings:['settings','model','data','experts','job','resources','evaluation','checkpoints','capabilities']};
 const missing=state?(required[active]||[]).filter(key=>state[key as keyof typeof state]==null):[],Component=page.component;
 return <>{group.pages.length>1&&<nav className="workspace-subnav" aria-label={group.name+' 작업'}>{group.pages.map(item=><a key={item.id} href={'#'+group.hash+'?tab='+item.id} aria-current={item.id===page.id?'page':undefined}>{item.name}</a>)}</nav>}{missing.length?<ErrorMessage message={missing.map(key=>key+': '+(state?.module_errors?.[key]||'상태 조회 실패')).join(' · ')}/>:<Suspense fallback={<p className="text-xs text-slate-500">화면을 여는 중입니다.</p>}><Component key={group.hash+page.id}/></Suspense>}</>;
}
export function Shell({active,children}:{active:string;children:ReactNode}){
 const {state,error,refresh,pending,execute}=useOperations(),[alerts,setAlerts]=useState(false),close=useCallback(()=>setAlerts(false),[]);
 const issues=state?.experts?.items.filter(item=>item.active&&item.inference?.reason)||[];
 return <div className="min-h-dvh bg-[#f4f6fa] text-slate-900">
  <header className="sticky top-0 z-30 border-b border-slate-200 bg-white"><div className="flex min-h-12 flex-wrap items-center justify-between gap-2 px-3 py-2">
   <a href="#control" className="flex items-center gap-2 text-sm font-bold"><Activity size={17} className="text-blue-600"/>FinRL <span className="hidden text-[11px] font-normal text-slate-400 sm:inline">SB3 SAC</span></a>
   <nav aria-label="주요 메뉴" className="flex items-center gap-1">{navigation.map(({hash,name,icon:Icon})=><a key={hash} href={'#'+hash} aria-current={active===hash?'page':undefined} className={'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold '+(active===hash?'bg-blue-50 text-blue-700':'text-slate-500 hover:bg-slate-50')}><Icon size={14}/>{name}</a>)}</nav>
   <div className="flex items-center gap-2"><Status tone={error?'bad':state?'good':'idle'}>{error?'연결 오류':state?'서버 연결':'연결 중'}</Status>{state?.job?.running&&<Button className="!rounded-md !px-2 !py-1 !text-xs" tone="danger" busy={pending.has('stop')} onClick={()=>void execute('stop',{})}>작업 중지</Button>}<button aria-label="새로고침" onClick={()=>void refresh()} className="p-1.5 text-slate-500"><RefreshCw size={15}/></button><button aria-label={'알림 '+issues.length+'개'} onClick={()=>setAlerts(true)} className="p-1.5 text-slate-500"><Bell size={15}/></button></div>
  </div></header>
  <main className={active==='moe'?'mx-auto max-w-[1440px] px-4 py-6 sm:px-7 sm:py-8':'workspace-compact px-3 py-3'}>
   {active==='moe'&&<h1 className="mb-5 text-xl font-bold">MoE</h1>}
   {state&&active!=='moe'&&<div className="mb-2 flex items-center justify-between gap-2 text-[11px] text-slate-400"><span>{navigation.find(item=>item.hash===active)?.name}</span><time>{date(state.updated_at)} 기준</time></div>}
   <ErrorMessage message={error}/>{state?.module_errors&&Object.entries(state.module_errors).map(([name,detail])=><ErrorMessage key={name} message={name+': '+detail}/>)}{children}
  </main>
  <Drawer title="현재 실행 · 알림" open={alerts} onClose={close}>{state?.job?.status&&<p className="mb-3 text-xs">{state.job.command} · {state.job.status} · {state.job.detail||date(state.job.started_at)}</p>}{issues.map(item=><p key={item.id} className="mb-2 text-xs text-amber-700">{item.name}: {item.inference?.reason}</p>)}{!issues.length&&!state?.job?.status&&<Empty title="현재 알림 기록이 없습니다."/>}</Drawer>
 </div>;
}
