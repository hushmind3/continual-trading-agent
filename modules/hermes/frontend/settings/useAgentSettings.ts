import {createContext,useContext,useEffect,useRef,useState} from 'react';
import {request} from '@platform/data/api';
import {prefix,failure,type Settings} from '../types';
export const SettingsActivity=createContext(true);
export function useAgentSettings() {
 const active=useContext(SettingsActivity),base=useRef<Settings|undefined>(undefined);
 const [cfg,setCfg]=useState<Settings>(),[error,setError]=useState(''),[revision,reload]=useState(0);
 const acceptCfg=(value:Settings)=>{base.current=value;setCfg(value)};
 useEffect(()=>{
  if(!active)return;
  let live=true;setError('');
  void request<Settings>(prefix+'settings',{},'GET').then(value=>{
   if(!live)return;
   const previousBase=base.current;base.current=value;
   setCfg(previous=>{
    if(!previous||!previousBase)return value;
    const merged={...value} as unknown as Record<string,unknown>;
    for(const key of Object.keys(previous) as (keyof Settings)[])if(JSON.stringify(previous[key])!==JSON.stringify(previousBase[key]))merged[key]=previous[key];
    return merged as unknown as Settings;
   });
  }).catch(error=>{if(live)setError(failure(error))});
  return()=>{live=false};
 },[active,revision]);
 return {cfg,setCfg,acceptCfg,error,setError,reload:()=>reload(value=>value+1)};
}
