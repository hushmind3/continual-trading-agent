import {createContext,useContext,useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button} from '@platform/ui/Primitives';
import {MessageBody} from './MessageBody';
import {failure} from '../types';

export const CompanyConversations=createContext<{id:string;title:string;session_id:string}[]>([]);
export const companySession=(id:string)=>'company:'+id;
export type Venture={id:string;name:string;status:string;proposal_json:string};
export type CompanyProgress={approved?:number;published?:boolean;free_trial?:boolean;payment_connected?:boolean;usage?:{requests?:number};product_url?:string;preview_url?:string;product_name?:string};
type State={session_id?:string;ventures:Venture[];progress?:CompanyProgress};
export function useCompanyConversation(selected:string){
 const sources=useContext(CompanyConversations),source=sources.find(v=>v.session_id===selected),id=source?.id??sources[0]?.id;
 const [state,setState]=useState<State>({ventures:[]}),[error,setError]=useState(''),[pending,setPending]=useState(false);
 useEffect(()=>{setState({ventures:[]});setError('');if(!id)return;let live=true,reading=false;
  const refresh=async()=>{if(reading)return;reading=true;try{const next=await request<State>('projects/conversation',{id},'GET');if(live)setState(previous=>JSON.stringify(previous)===JSON.stringify(next)?previous:next)}catch(e){if(live)setError(failure(e))}finally{reading=false}};
  void refresh();const timer=setInterval(()=>{if(!document.hidden)void refresh()},2500);return()=>{live=false;clearInterval(timer)};
 },[id]);
 const decide=async(venture_id:string,approve:boolean)=>{if(!id)return;setPending(true);setError('');try{const result=await request<{session_id:string;name:string}>('projects/conversation',{id,action:'decision',venture_id,approve});setState(await request<State>('projects/conversation',{id},'GET'));return result}catch(e){setError(failure(e));throw e}finally{setPending(false)}};
 return {sources,enabled:!!source,id,ventures:state.ventures.filter(v=>v.status==='pending'),progress:state.progress,error,pending,decide};
}

export function CompanyApprovals({items,pending,readOnly,decide}:{items:Venture[];pending:boolean;readOnly:boolean;decide:(id:string,approve:boolean)=>void}){
 return <>{items.map(item=><section key={item.id} aria-label={'사업안 승인: '+item.name} className="hermes-approval"><b>{item.name}</b><details><summary>사업안 보기</summary><MessageBody text={(()=>{try{return JSON.stringify(JSON.parse(item.proposal_json),null,2)}catch{return item.proposal_json}})()}/></details><div className="hermes-actions"><Button tone="primary" disabled={pending||readOnly} title={readOnly?'읽기 모드를 끄면 승인 후 실행할 수 있습니다':undefined} onClick={()=>decide(item.id,true)}>승인 후 실행</Button><Button disabled={pending} onClick={()=>decide(item.id,false)}>보류</Button></div>{readOnly&&<p>읽기 모드에서는 사업 실행을 승인할 수 없습니다.</p>}</section>)}</>;
}
