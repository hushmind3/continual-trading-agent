import {useRef,useState,type ChangeEvent} from 'react';
import {Upload} from 'lucide-react';
import {Button,ErrorMessage} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {request} from '@platform/data/api';
import type {Project} from './types';

export function PackageTransfer({busy,onInstalled}:{busy:boolean;onInstalled:(project:Project)=>void}){
 const input=useRef<HTMLInputElement>(null);
 const [sending,setSending]=useState(false),[error,setError]=useState('');
 async function upload(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];event.target.value='';if(!file)return;
  if(file.size>32*1024*1024){setError('32 MiB 이하의 앱 ZIP을 선택하세요.');return}
  setSending(true);setError('');
  try{
   const archive=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('앱 파일을 읽을 수 없습니다.'));reader.readAsDataURL(file)});
   const project=await request<Project>('projects/import',{archive});onInstalled(project);
  }catch(e){setError(String(e))}finally{setSending(false)}
 }
 return <Panel title="앱 파일에서 설치"><div className="flex flex-wrap items-center justify-between gap-4"><p className="text-sm text-slate-500">내보낸 앱 ZIP을 선택하면 다운로드와 모델 변환 없이 설치·실행 연결을 진행합니다.</p><input ref={input} className="hidden" type="file" accept=".zip,application/zip" aria-label="앱 패키지 파일" onChange={event=>void upload(event)}/><Button disabled={busy} busy={sending} onClick={()=>input.current?.click()}><Upload size={16}/>앱 파일 선택</Button></div><ErrorMessage message={error}/></Panel>;
}
