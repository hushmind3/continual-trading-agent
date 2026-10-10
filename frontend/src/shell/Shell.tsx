import {useCallback,useState,type ReactNode} from "react";
import {Activity,Bell,Boxes,ChartCandlestick,CircuitBoard,GraduationCap,Link2,LockKeyhole,Wallet,RefreshCw} from "lucide-react";
import {useOperations} from "../data/Operations";
import {Button,Drawer,Empty,ErrorMessage,Status} from "../ui/Primitives";
import {date} from "../ui/format";
export const navigation=[
  {hash:"control",name:"운영",icon:Activity},{hash:"moe",name:"MoE",icon:Boxes},
  {hash:"markets",name:"시장",icon:ChartCandlestick},{hash:"portfolio",name:"계좌",icon:Wallet},
  {hash:"learning",name:"학습",icon:GraduationCap},{hash:"connection",name:"연결",icon:Link2},
  {hash:"system",name:"진단",icon:CircuitBoard},
];
export function Shell({active,children}:{active:string;children:ReactNode}) {
  const {state,error,refresh,pending}=useOperations();
  const [alerts,setAlerts]=useState(false);
  const close=useCallback(()=>setAlerts(false),[]);
  const issues=state?.experts.items.filter(e=>e.active&&e.inference?.reason)||[];
  return <div className="min-h-dvh bg-[#f4f6fa] text-slate-900">
    <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex min-h-16 max-w-[1500px] flex-wrap items-center justify-between gap-x-5 gap-y-3 px-4 py-3 sm:px-7 lg:flex-nowrap">
        <a href="#control" className="flex shrink-0 items-center gap-2.5 font-bold tracking-tight"><span className="grid size-8 place-items-center rounded-xl bg-blue-600 text-white"><Activity size={19}/></span><span>FinRL-X<span className="ml-2 text-xs font-medium text-slate-400">MoE · SAC</span></span></a>
        <nav aria-label="주요 화면" className="order-3 grid w-full grid-cols-4 gap-1 sm:flex sm:w-auto sm:flex-1 sm:justify-center lg:order-2">{navigation.map(({hash,name,icon:Icon})=><a key={hash} href={'#'+hash} aria-current={active===hash?'page':undefined} className={'flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-[13px] font-semibold transition hover:bg-slate-50 '+(active===hash?'bg-blue-50 text-blue-700':'text-slate-500')}><Icon size={16}/>{name}</a>)}</nav>
        <div className="order-2 flex items-center gap-3 lg:order-3"><span className="hidden items-center gap-1.5 text-xs text-slate-400 sm:flex"><LockKeyhole size={13}/>실주문 미연결</span><Status tone={error?'bad':state?'good':'idle'}>{error?'연결 끊김':state?'서버 연결':'연결 중'}</Status><Button className="!bg-transparent !px-2" aria-label={'알림 '+issues.length+'개'} onClick={()=>setAlerts(true)}><Bell size={18}/></Button></div>
      </div>
    </header>
    <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-7 sm:py-8"><div className="mb-5 flex flex-wrap items-center justify-between gap-3"><h1 className="text-xl font-bold tracking-tight">{navigation.find(n=>n.hash===active)?.name||'운영'}</h1><div className="flex items-center gap-3">{state&&<time className="text-xs tabular-nums text-slate-400">{date(state.updated_at)} 기준</time>}<Button busy={pending.has('state')} className="!px-3 !py-2 !text-xs" onClick={()=>void refresh()}><RefreshCw size={13}/>새로고침</Button></div></div>{error&&<div className="mb-5"><ErrorMessage message={error}/></div>}{children}</main>
    <Drawer title="알림 · 현재 기록" open={alerts} onClose={close}><p className="mb-4 text-xs leading-5 text-slate-400">현재 작업과 마지막 실제 Expert 추론 기록</p>{state?.job.status&&<div className="mb-4 rounded-xl bg-slate-50 p-4"><b className="text-sm">{state.job.command} · {state.job.status}</b><p className="mt-2 text-xs text-slate-500">{state.job.detail||date(state.job.started_at)}</p></div>}{issues.map(e=><div key={e.id} className="mb-3 rounded-xl bg-amber-50 p-4"><b className="text-sm">{e.name}</b><p className="mt-2 text-xs leading-5 text-amber-800">{e.inference?.reason}</p></div>)}{!issues.length&&!state?.job.status&&<Empty title="현재 알림 기록이 없습니다."/>}</Drawer>
  </div>;
}
