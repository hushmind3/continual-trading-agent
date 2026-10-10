import {createContext,useCallback,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {request} from './api';
import type {Snapshot} from './types';
interface Context {
  state:Snapshot|null;error:string;pending:Set<string>;refresh:()=>Promise<void>;
  execute:<T>(path:string,body:unknown)=>Promise<T>;
}
const Operations=createContext<Context|null>(null);
export function OperationsProvider({children}:{children:ReactNode}) {
  const [state,setState]=useState<Snapshot|null>(null),[error,setError]=useState(''),[pending,setPending]=useState(new Set<string>());
  const sequence=useRef(0),applied=useRef(0);
  const refresh=useCallback(async()=>{
    const revision=++sequence.current;
    try {const next=await request<Snapshot>('state');if(next.architecture!=='finrlx-official-sac-v2')throw new Error('현재 SAC API가 아닌 서버에 연결되어 있습니다.');
      if(revision<applied.current)return;applied.current=revision;setState(next);setError('');
    }catch(e){if(revision<applied.current)return;applied.current=revision;setError(e instanceof Error?e.message:'연결 실패');}
  },[]);
  useEffect(()=>{let disposed=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{if(disposed)return;await refresh();if(!disposed)timer=setTimeout(poll,4000)};void poll();return()=>{disposed=true;clearTimeout(timer)}},[refresh]);
  const execute=async<T,>(path:string,body:unknown):Promise<T>=>{
    setPending(old=>new Set(old).add(path));try{const result=await request<T>(path,body);await refresh();return result}
    finally{setPending(old=>{const next=new Set(old);next.delete(path);return next})}
  };
  return <Operations.Provider value={{state,error,pending,refresh,execute}}>{children}</Operations.Provider>;
}
export function useOperations(){const context=useContext(Operations);if(!context)throw new Error('OperationsProvider가 필요합니다.');return context;}
