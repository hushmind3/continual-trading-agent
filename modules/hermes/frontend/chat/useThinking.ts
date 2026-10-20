import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {prefix,failure,type Settings} from '../types';
import type {CodexModel} from '../settings/models/ReasoningSelect';
export type ThinkingMode='auto'|'on'|'off';
const valid=(value:unknown):value is ThinkingMode=>value==='auto'||value==='on'||value==='off';
const key=(model:string)=>'hermes.thinking.'+model;
export function useThinking(model:string){
 const [value,setValue]=useState<ThinkingMode>('auto'),[local,setLocal]=useState(false);
 const [cloud,setCloud]=useState(false),[effort,setEffort]=useState('auto'),[metadata,setMetadata]=useState<CodexModel>(),[error,setError]=useState('');
 useEffect(()=>{
  let live=true;setLocal(false);setCloud(false);setMetadata(undefined);setError('');
  void request<Settings>(prefix+'settings',{},'GET').then(cfg=>{
   if(!live)return;let saved:string|null=null;
   try{saved=localStorage.getItem(key(model))}catch{/* Preferences also work without storage. */}
   setValue(valid(saved)?saved:cfg.thinking_mode??'auto');setLocal(!!cfg.local_model);
   if(cfg.provider==='openai-codex'){
    setCloud(true);setEffort(cfg.reasoning_effort??'auto');
    void request<{models:CodexModel[]}>(prefix+'codex/models',{}).then(result=>{if(live)setMetadata(result.models.find(row=>row.id===model||row.aliases?.includes(model)))}).catch(error=>{if(live)setError(failure(error))});
   }
  }).catch(()=>{});
  return()=>{live=false};
 },[model]);
 const change=(next:ThinkingMode)=>{setValue(next);try{localStorage.setItem(key(model),next)}catch{/* Keep the current choice. */}};
 const prepare=async()=>{if(local)await request(prefix+'settings',{thinking_mode:value});if(cloud)await request(prefix+'settings',{reasoning_effort:effort})};
 return {value,change,local,prepare,reasoning:cloud?{model:metadata,value:effort,change:setEffort,error}:undefined};
}
