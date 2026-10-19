import {createContext,useContext,useEffect,useMemo,useState} from 'react';
import {request} from '@platform/data/api';
import {Button} from '@platform/ui/Primitives';
import {MessageBody} from './MessageBody';
import {failure,type Job,type Message} from '../types';

export const CompanyConversations=createContext<{id:string;title:string}[]>([]);
export const companySession=(id:string)=>'company:'+id;
export type Venture={id:string;name:string;status:string;proposal_json:string};
export type CompanyProgress={published?:boolean;free_trial?:boolean;payment_connected?:boolean;usage?:{requests?:number};product_url?:string};
type State={messages:{speaker:string;body:string}[];ventures:Venture[];progress?:CompanyProgress;request?:{status:string;error:string}};
export function useCompanyConversation(selected:string){
 const sources=useContext(CompanyConversations),source=sources.find(v=>companySession(v.id)===selected),id=source?.id??sources[0]?.id;
 const [state,setState]=useState<State>({messages:[],ventures:[]}),[job,setJob]=useState<Job>(),[error,setError]=useState(''),[pending,setPending]=useState(false);
 const key='hermes.company.request.'+(id||''),[requestId,setRequestId]=useState('');
 useEffect(()=>{setState({messages:[],ventures:[]});setJob(undefined);setError('');setRequestId(id?localStorage.getItem(key)||'':'')},[id]);
 useEffect(()=>{if(!id)return;let live=true,reading=false;
  const refresh=async()=>{if(reading)return;reading=true;try{
   const next=await request<State>('projects/conversation',{id,request_id:requestId},'GET');
   if(!live)return;setState(previous=>JSON.stringify(previous)===JSON.stringify(next)?previous:next);setError(next.request?.error||'');
   if(next.request&&next.request.status!=='working'){localStorage.removeItem(key);setRequestId('')}
  }catch(e){if(live)setError(failure(e))}finally{reading=false}};
  let measuring=false;const metrics=async()=>{if(measuring)return;measuring=true;try{const activity=await request<{job?:Job}>('projects/harness',{id},'GET');if(live)setJob(previous=>JSON.stringify(previous)===JSON.stringify(activity.job)?previous:activity.job)}catch{/* History errors remain independent of measured progress. */}finally{measuring=false}};
  void refresh();void metrics();const timer=setInterval(()=>{if(!document.hidden)void refresh()},2500),measureTimer=setInterval(()=>{if(!document.hidden)void metrics()},1000);return()=>{live=false;clearInterval(timer);clearInterval(measureTimer)};
 },[id,requestId]);
 const send=async(message:string)=>{if(!id)return;setError('');setPending(true);try{const result=await request<{request_id:string}>('projects/conversation',{id,action:'send',message});localStorage.setItem(key,result.request_id);setRequestId(result.request_id)}finally{setPending(false)}};
 const decide=async(venture_id:string,approve:boolean)=>{if(!id)return;setPending(true);setError('');try{await request('projects/conversation',{id,action:'decision',venture_id,approve});setState(await request<State>('projects/conversation',{id},'GET'))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const messages:Message[]=useMemo(()=>state.messages.map(m=>({role:m.speaker==='owner'?'user':'assistant',content:m.body})),[state.messages]);
 return {sources,enabled:!!source,id,messages,ventures:state.ventures.filter(v=>v.status==='pending'),progress:state.progress,job,error,pending,waiting:!!source&&!!requestId,send,decide};
}

export function CompanyApprovals({items,pending,readOnly,decide}:{items:Venture[];pending:boolean;readOnly:boolean;decide:(id:string,approve:boolean)=>void}){
 return <>{items.map(item=><section key={item.id} aria-label={'사업안 승인: '+item.name} className="hermes-approval"><b>{item.name}</b><details><summary>사업안 보기</summary><MessageBody text={(()=>{try{return JSON.stringify(JSON.parse(item.proposal_json),null,2)}catch{return item.proposal_json}})()}/></details><div className="hermes-actions"><Button tone="primary" disabled={pending||readOnly} title={readOnly?'읽기 모드를 끄면 승인 후 실행할 수 있습니다':undefined} onClick={()=>decide(item.id,true)}>승인 후 실행</Button><Button disabled={pending} onClick={()=>decide(item.id,false)}>보류</Button></div>{readOnly&&<p>읽기 모드에서는 사업 실행을 승인할 수 없습니다.</p>}</section>)}</>;
}
