import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
export function useKorean(texts:string[],enabled=true){
 const [translations,setTranslations]=useState<Record<string,string>>({}),[state,setState]=useState(''),[detail,setDetail]=useState('');
 const key=JSON.stringify([...new Set(texts.filter(text=>text&&text.length<=6000))].slice(0,200));
 useEffect(()=>{if(!enabled){setState('');return}let active=true;let timer:ReturnType<typeof setTimeout>;
  async function poll(){try{const result=await request<{translations:Record<string,string>;state:string;detail?:string}>('projects/localize',{texts:JSON.parse(key)});if(!active)return;setTranslations(previous=>({...previous,...result.translations}));setState(result.state);setDetail(result.detail||'');if(result.state==='pending')timer=setTimeout(poll,1500)}catch(error){if(active){setState('unavailable');setDetail(String(error))}}}
  if(JSON.parse(key).length)void poll();return()=>{active=false;clearTimeout(timer)};
 },[key,enabled]);
 return {text:(value:string)=>enabled?translations[value.trim()]||value:value,state,detail};
}
