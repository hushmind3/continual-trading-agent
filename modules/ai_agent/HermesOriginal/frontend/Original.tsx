import {useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
import {ExternalLink,Play,Square} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage,Status} from '@platform/ui/Primitives';

type State={state:'ready'|'starting'|'stopped';url:string;revision:string};
const prefix='ai_agent/HermesOriginal/';
export function Original(){
 const [header,setHeader]=useState<HTMLElement|null>(null);
 useEffect(()=>setHeader(document.getElementById('workspace-header-slot')),[]);
 const [state,setState]=useState<State>(),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{let cancelled=false;let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{const next=await request<State>(prefix+'status',{},'GET');
   if(cancelled)return;setState(next);if(next.state==='starting')timer=setTimeout(()=>void poll(),1500);
  }catch(e){if(!cancelled)setError(e instanceof Error?e.message:String(e))}};
  void poll();return()=>{cancelled=true;clearTimeout(timer)};
 },[busy]);
 const act=async(command:string)=>{setBusy(true);setError('');try{setState(await request<State>(prefix+command))}
  catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false)}};
 return <section className="ui-app-workspace hermes-original-workspace">
  {header&&createPortal(<div className="hermes-original-controls" aria-label="헤르메스 실행 제어">
   <span className="hidden sm:inline-flex"><Status tone={state?.state==='ready'?'good':'idle'}>{state?.state==='ready'?'실행 중':state?.state==='starting'?'준비 중':'중지됨'}</Status></span>
   {state?.url&&<Button className="workspace-icon-button" aria-label="새 창에서 열기" title="새 창에서 열기" onClick={()=>window.open(state.url,'_blank','noopener')}><ExternalLink size={17}/></Button>}
   {state?.state==='stopped'?<Button className="workspace-icon-button" aria-label="실행" title="실행" busy={busy} onClick={()=>void act('start')}><Play size={17}/></Button>:
    <Button className="workspace-icon-button" aria-label="중지" title="중지" busy={busy} onClick={()=>void act('stop')}><Square size={17}/></Button>}
  </div>,header)}
  {error&&<ErrorMessage message={error}/>}
  {state?.url&&<iframe title="Hermes Agent 원본" src={state.url} className="ui-app-workspace-frame" allow="clipboard-read; clipboard-write; microphone; camera; fullscreen"/>}
 </section>;
}
