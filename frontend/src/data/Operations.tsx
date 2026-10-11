import {createContext,useCallback,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {request} from './api';
import type {Snapshot} from './types';
interface Context {
  state:Snapshot|null;error:string;pending:Set<string>;refresh:()=>Promise<void>;
  observe:(path:string)=>()=>void;execute:<T>(path:string,body:unknown)=>Promise<T>;
}
const Operations=createContext<Context|null>(null);
export function OperationsProvider({children}:{children:ReactNode}) {
  const [state,setState]=useState<Snapshot|null>(null),[error,setError]=useState(''),[pending,setPending]=useState(new Set<string>());
  const views=useRef(new Map<string,number>()),inFlight=useRef<Promise<void>|null>(null),scheduled=useRef(false),alive=useRef(true),lastSelection=useRef('');
  const refresh=useCallback((force=true):Promise<void>=>{
    if(inFlight.current)return inFlight.current;
    const selection=JSON.stringify([...views.current.keys()].sort());
    lastSelection.current=selection;
    const run=(async()=>{
      try{
        const next=await request<Snapshot>('state',{views:selection,refresh_views:force});
        if(next.architecture!=='finrl-unified-v3')throw new Error('통합 상태 API가 아닌 서버에 연결되어 있습니다.');
        if(alive.current){setState(next);setError('');}
      }catch(e){if(alive.current)setError(e instanceof Error?e.message:'연결 실패');}
    })();
    inFlight.current=run;
    void run.finally(()=>{inFlight.current=null;});
    return run;
  },[]);
  const schedule=useCallback(()=>{
    if(scheduled.current)return;scheduled.current=true;
    queueMicrotask(()=>{scheduled.current=false;void (async()=>{await inFlight.current;if(alive.current&&JSON.stringify([...views.current.keys()].sort())!==lastSelection.current)await refresh(false);})();});
  },[refresh]);
  const observe=useCallback((path:string)=>{
    const count=views.current.get(path)||0;views.current.set(path,count+1);if(!count)schedule();
    return()=>{const remaining=(views.current.get(path)||1)-1;if(remaining)views.current.set(path,remaining);else views.current.delete(path);};
  },[schedule]);
  useEffect(()=>{alive.current=true;let disposed=false;let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{if(disposed)return;await refresh(false);if(!disposed)timer=setTimeout(poll,4000)};void poll();
    return()=>{disposed=true;alive.current=false;clearTimeout(timer)};
  },[refresh]);
  const execute=async<T,>(path:string,body:unknown):Promise<T>=>{
    setPending(old=>new Set(old).add(path));
    try{const result=await request<T>(path,body);await inFlight.current;await refresh(false);return result}
    finally{setPending(old=>{const next=new Set(old);next.delete(path);return next})}
  };
  return <Operations.Provider value={{state,error,pending,refresh,observe,execute}}>{children}</Operations.Provider>;
}
export function useOperations(){const context=useContext(Operations);if(!context)throw new Error('OperationsProvider가 필요합니다.');return context;}
export function useSystemState<T>(path:string|null){
  const {state,error,refresh,observe}=useOperations();
  useEffect(()=>path?observe(path):undefined,[path,observe]);
  const value=path?state?.views?.[path]:undefined;
  return {data:(value?.data as T|undefined)??null,error:value?.error||error,loading:!!path&&!value,refresh};
}
