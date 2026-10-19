import {useCallback,useEffect,useRef,useState} from 'react';
import {request} from '@platform/data/api';
import {AppError,invoke} from './api';
import type {Harness,WorkspaceData} from './types';
export function useWorkspace(id:string){
 const [token,setToken]=useState(''),[login,setLogin]=useState(false),[data,setData]=useState<WorkspaceData|null>(null),[harness,setHarness]=useState<Harness>({}),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const locked=useRef(false),mounted=useRef(true);
 const refresh=useCallback(async()=>{
  if(!token||locked.current)return;locked.current=true;
  try{const [next,state]=await Promise.all([invoke<WorkspaceData>(id,'/api/admin/platform/workspace',token),request<Harness>('projects/harness',{id},'GET')]);if(mounted.current){setData(next);setHarness(state);setError('')}}
  catch(e){if(mounted.current){setError(String(e));if(e instanceof AppError&&e.status===401)setLogin(true)}}finally{locked.current=false}
 },[id,token]);
 useEffect(()=>{mounted.current=true;void invoke<{token:string}>(id,'/api/local/session').then(v=>{if(mounted.current)setToken(v.token)}).catch(()=>{if(mounted.current)setLogin(true)});return()=>{mounted.current=false}},[id]);
 useEffect(()=>{void refresh();const timer=setInterval(()=>{if(!document.hidden)void refresh()},3000);return()=>clearInterval(timer)},[refresh]);
 async function authenticate(value:string){try{await invoke(id,'/api/admin/platform/workspace',value);setToken(value);setLogin(false);setError('')}catch(e){setError(String(e))}}
 async function action<T>(path:string,body:unknown){setBusy(true);setError('');try{const value=await invoke<T>(id,path,token,body);await refresh();return value}catch(e){setError(String(e));throw e}finally{if(mounted.current)setBusy(false)}}
 return {data,harness,error,busy,login,authenticate,action,refresh,reportError:(e:unknown)=>setError(String(e))};
}
