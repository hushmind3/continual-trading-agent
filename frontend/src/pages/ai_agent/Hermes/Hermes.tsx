import {useEffect,useRef,useState} from 'react';
import {request} from '../../../data/api';
import {Button,ErrorMessage} from '../../../ui/Primitives';
import {Chat} from './chat/Chat';
import {Settings as AgentSettings} from './settings/Settings';
import {prefix,failure,working,type AgentStatus,type Settings} from './types';
import './Hermes.css';
import './Workspace.css';

export function Hermes(){
 const [tab,setTab]=useState('chat'),[status,setStatus]=useState<AgentStatus>(),[error,setError]=useState('');
 const [modelName,setModelName]=useState(''),[focused,setFocused]=useState(()=>sessionStorage.getItem('hermes.focused')==='true');
 const [retry,setRetry]=useState(0),last=useRef('');
 const polling=working(status)||status?.local_model.state==='loading';
 const refreshModel=()=>{void request<Settings>(prefix+'settings',{},'GET').then(s=>setModelName(s.model)).catch(()=>{})};
 useEffect(refreshModel,[]);
 useEffect(()=>{let disposed=false,inFlight=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{
  clearTimeout(timer);if(inFlight||disposed)return;inFlight=true;
  try{const next=await request<AgentStatus>(prefix+'status',{},'GET');if(!disposed){const key=JSON.stringify(next);if(key!==last.current){last.current=key;setStatus(next)}setError('');if(working(next)||next.local_model.state==='loading')timer=setTimeout(()=>void poll(),document.hidden?10000:1200)}}catch(e){if(!disposed){setError(failure(e));if(polling)timer=setTimeout(()=>void poll(),10000)}}finally{inFlight=false}
 };const resume=()=>{if(!document.hidden)void poll()};void poll();window.addEventListener('focus',resume);document.addEventListener('visibilitychange',resume);return()=>{disposed=true;clearTimeout(timer);window.removeEventListener('focus',resume);document.removeEventListener('visibilitychange',resume)}},[retry,polling]);
 const focus=()=>setFocused(v=>{sessionStorage.setItem('hermes.focused',String(!v));return !v});
 const models=()=>{sessionStorage.setItem('hermes.settings.tab','models');setTab('settings')};
 return <div className={'hermes-workspace '+(tab==='chat'?'is-chat':'is-settings')+(focused?' is-focused':'')}>
 {error&&<div className="ha-connection-error"><ErrorMessage message={error}/><Button onClick={()=>setRetry(v=>v+1)}>다시 연결</Button></div>}
 <div className="hermes-chat-mount" hidden={tab!=='chat'}><Chat status={status} modelName={modelName} focused={focused} onFocus={focus} onStatus={setStatus} onModels={models} onSettings={()=>setTab('settings')} onRefresh={()=>setRetry(v=>v+1)}/></div>
 {tab==='settings'&&<AgentSettings status={status} onStatus={setStatus} onChat={()=>{setTab('chat');refreshModel()}}/>}
 </div>;
}
