import {useCallback,useEffect,useRef,useState} from 'react';
import {request} from './api';
export function useEndpoint<T>(path:string|null) {
  const [data,setData]=useState<T|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),revision=useRef(0);
  const refresh=useCallback(async()=>{if(!path)return;const current=++revision.current;setLoading(true);
    try{const next=await request<T>(path);if(current===revision.current){setData(next);setError('')}}
    catch(e){if(current===revision.current)setError(e instanceof Error?e.message:'조회 실패')}
    finally{if(current===revision.current)setLoading(false)}
  },[path]);
  useEffect(()=>{setData(null);setError('');void refresh();return()=>{revision.current++}},[refresh]);
  return {data,error,loading,refresh};
}
