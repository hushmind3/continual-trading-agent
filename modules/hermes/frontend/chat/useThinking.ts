import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {prefix,type Settings} from '../types';
export type ThinkingMode='auto'|'on'|'off';
const valid=(value:unknown):value is ThinkingMode=>value==='auto'||value==='on'||value==='off';
const key=(model:string)=>'hermes.thinking.'+model;
export function useThinking(model:string){
 const [value,setValue]=useState<ThinkingMode>('auto'),[local,setLocal]=useState(false);
 useEffect(()=>{
  let live=true;setLocal(false);
  void request<Settings>(prefix+'settings',{},'GET').then(cfg=>{
   if(!live)return;let saved:string|null=null;
   try{saved=localStorage.getItem(key(model))}catch{/* Preferences also work without storage. */}
   setValue(valid(saved)?saved:cfg.thinking_mode??'auto');setLocal(!!cfg.local_model);
  }).catch(()=>{});
  return()=>{live=false};
 },[model]);
 const change=(next:ThinkingMode)=>{setValue(next);try{localStorage.setItem(key(model),next)}catch{/* Keep the current choice. */}};
 const prepare=async()=>{if(local)await request(prefix+'settings',{thinking_mode:value})};
 return {value,change,local,prepare};
}
