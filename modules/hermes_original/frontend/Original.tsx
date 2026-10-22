import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage,Status} from '@platform/ui/Primitives';

type State={state:'ready'|'starting'|'stopped';url:string;revision:string};
const prefix='ai_agent/HermesOriginal/';
export function Original(){
 const [state,setState]=useState<State>(),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{let cancelled=false;let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{const next=await request<State>(prefix+'status',{},'GET');
   if(cancelled)return;setState(next);if(next.state==='starting')timer=setTimeout(()=>void poll(),1500);
  }catch(e){if(!cancelled)setError(e instanceof Error?e.message:String(e))}};
  void poll();return()=>{cancelled=true;clearTimeout(timer)};
 },[busy]);
 const act=async(command:string)=>{setBusy(true);setError('');try{setState(await request<State>(prefix+command))}
  catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false)}};
 return <section className="flex h-full min-h-0 flex-col">
  <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-3">
   <div className="flex items-center gap-3"><h1 className="font-semibold">헤르메스 원본</h1>
    <Status tone={state?.state==='ready'?'good':'idle'}>{state?.state==='ready'?'실행 중':state?.state==='starting'?'원본 준비 중':'중지됨'}</Status></div>
   <div className="flex items-center gap-2">{state?.url&&<Button onClick={()=>window.open(state.url,'_blank','noopener')}>원본 새 창</Button>}
    {state?.state==='stopped'?<Button tone="primary" busy={busy} onClick={()=>void act('start')}>원본 실행</Button>:
     <Button busy={busy} onClick={()=>void act('stop')}>중지</Button>}</div>
  </header>
  {error&&<ErrorMessage message={error}/>}
  {state?.url&&<iframe title="Hermes Agent 원본" src={state.url} className="min-h-0 w-full flex-1 border-0" allow="clipboard-read; clipboard-write; microphone; camera; fullscreen"/>}
 </section>;
}
