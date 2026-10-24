import {useEffect,useRef,useState} from 'react';
import {Download,MousePointer2,Send,Square} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage,Status} from '@platform/ui/Primitives';

type Message={role:'user'|'assistant';text:string;time:number};
type State={
 installed:boolean;installing:boolean;install_error:string;running:boolean;busy:boolean;
 progress:string;history:Message[];log:string;target:string;model:string;
};
const prefix='ai_agent/HermesOperator/';

export function HermesOperator(){
 const [state,setState]=useState<State>();
 const [text,setText]=useState('');
 const [error,setError]=useState('');
 const bottom=useRef<HTMLDivElement|null>(null);

 const refresh=async()=>{try{setState(await request<State>(prefix+'status',{},'GET'));setError('')}
  catch(e){setError(e instanceof Error?e.message:String(e))}};
 useEffect(()=>{void refresh();const timer=setInterval(()=>void refresh(),1000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{bottom.current?.scrollIntoView({behavior:'smooth'})},[state?.history.length,state?.progress]);

 const act=async(path:string,body:Record<string,unknown>={})=>{
  setError('');
  try{setState(await request<State>(prefix+path,body));}
  catch(e){setError(e instanceof Error?e.message:String(e))}
 };
 const send=async()=>{
  const message=text.trim();if(!message||state?.busy)return;
  setText('');await act('chat',{message});
 };

 return <section className="ui-app-workspace flex min-h-0 flex-col gap-3 p-4">
  <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-black/10 p-3">
   <MousePointer2 size={18}/>
   <strong>Hermes 외부 조종기</strong>
   <Status tone={state?.installed?'good':'idle'}>{state?.installing?'설치 중':state?.installed?'준비됨':'미설치'}</Status>
   {state?.running&&<Status tone={state.busy?'warn':'good'}>{state.busy?'조작 중':'브라우저 실행 중'}</Status>}
   <span className="text-xs opacity-60">{state?.model||'FreeLLMAPI · auto'}</span>
   <div className="ml-auto flex gap-2">
    {!state?.installed&&<Button tone="primary" busy={state?.installing} onClick={()=>void act('install')}><Download size={16}/>Browser Use 설치</Button>}
    {state?.running&&<Button onClick={()=>void act('stop')}><Square size={15}/>종료</Button>}
   </div>
  </div>

  {error&&<ErrorMessage message={error}/>}
  {state?.install_error&&<ErrorMessage message={state.install_error}/>}

  <div className="min-h-0 flex-1 overflow-auto rounded-xl border border-white/10 p-4">
   {!state?.history.length&&<div className="mx-auto max-w-2xl py-10 text-center opacity-70">
    <p className="font-medium">말로 시키면 보이는 Chromium 창에서 Hermes를 직접 조작합니다.</p>
    <p className="mt-2 text-sm">예: “연구원에게 시장조사 시키고 칸반에 작업 3개 만들어.”</p>
   </div>}
   <div className="mx-auto flex max-w-3xl flex-col gap-3">
    {state?.history.map((message,index)=><div key={index} className={message.role==='user'?'ml-auto max-w-[85%] rounded-2xl bg-white/10 px-4 py-3':'mr-auto max-w-[90%] rounded-2xl border border-white/10 px-4 py-3'}>
     <div className="whitespace-pre-wrap text-sm">{message.text}</div>
    </div>)}
    {state?.busy&&<div className="mr-auto rounded-2xl border border-white/10 px-4 py-3 text-sm opacity-70">{state.progress||'조작 중…'}</div>}
    <div ref={bottom}/>
   </div>
  </div>

  <div className="mx-auto flex w-full max-w-3xl gap-2">
   <textarea className="min-h-20 flex-1 resize-none rounded-xl border border-white/10 bg-transparent p-3 outline-none"
    value={text} disabled={!state?.installed||state?.installing}
    placeholder={state?.installed?'Hermes에 시킬 일을 말하세요':'먼저 Browser Use를 설치하세요.'}
    onChange={e=>setText(e.target.value)}
    onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();void send()}}}/>
   <Button tone="primary" disabled={!state?.installed||!text.trim()||state?.busy} busy={state?.busy} onClick={()=>void send()}><Send size={16}/>실행</Button>
  </div>
 </section>;
}
