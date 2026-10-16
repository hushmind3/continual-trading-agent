import {useEffect,useState} from 'react';
import {request} from '../../../../data/api';
import {prefix,failure,type Settings} from '../types';

export function useAgentSettings() {
  const [cfg,setCfg]=useState<Settings>(),[error,setError]=useState(''),[revision,reload]=useState(0);
  useEffect(()=>{let live=true;setError('');void request<Settings>(prefix+'settings',{},'GET').then(value=>{if(live)setCfg(value)}).catch(error=>{if(live)setError(failure(error))});return()=>{live=false}},[revision]);
  return {cfg,setCfg,error,setError,reload:()=>reload(value=>value+1)};
}
