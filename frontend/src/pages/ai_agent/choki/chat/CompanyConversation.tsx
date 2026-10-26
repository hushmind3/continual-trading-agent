import {createContext,useContext,useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button} from '@platform/ui/Primitives';
import {MessageBody} from './MessageBody';
import {failure,type Session} from '../types';

export const CompanyConversations=createContext<{id:string;title:string;session_id:string}[]>([]);
export const companySession=(id:string)=>'company:'+id;
export type Venture={id:string;name:string;status:string;proposal_json:string};
export type CompanyProgress={approved?:number;ready_products?:number;published?:boolean;free_trial?:boolean;payment_connected?:boolean;usage?:{requests?:number};product_url?:string;preview_url?:string;product_name?:string};
type State={session_id?:string;ventures:Venture[];progress?:CompanyProgress};
export function useCompanyConversation(selected:string,sessions:Session[]){
 const sources=useContext(CompanyConversations),source=sources.find(v=>v.session_id===selected||v.id===sessions.find(row=>row.id===selected)?.company_id),id=source?.id??sources[0]?.id;
 const [state,setState]=useState<State>({ventures:[]}),[error,setError]=useState(''),[pending,setPending]=useState(false);
 useEffect(()=>{setState({ventures:[]});setError('');if(!id||!source)return;let live=true,reading=false;
  const refresh=async()=>{if(reading)return;reading=true;try{const next=await request<State>('projects/conversation',{id},'GET');if(live)setState(previous=>JSON.stringify(previous)===JSON.stringify(next)?previous:next)}catch(e){if(live)setError(failure(e))}finally{reading=false}};
  void refresh();const timer=setInterval(()=>{if(!document.hidden)void refresh()},2500);return()=>{live=false;clearInterval(timer)};
 },[id,!!source]);
 const decide=async(venture_id:string,approve:boolean)=>{if(!id)return;setPending(true);setError('');try{const result=await request<{session_id:string;name:string;workspace:string}>('projects/conversation',{id,action:'decision',venture_id,approve});setState(await request<State>('projects/conversation',{id},'GET'));return result}catch(e){setError(failure(e));throw e}finally{setPending(false)}};
 return {sources,choices:sources.map(item=>item.id===source?.id?{...item,session_id:selected}:{...item,session_id:(()=>{const remembered=sessionStorage.getItem('hermes.company-session.'+item.id);return sessions.some(row=>row.id===remembered&&row.company_id===item.id)?remembered!:item.session_id})()}),root:source?.session_id===selected,enabled:!!source,id,ventures:state.ventures.filter(v=>v.status==='pending'),progress:state.progress,error,pending,decide};
}

const proposalLabels:Record<string,string>={problem:'고객 문제',product:'제품',solution:'해결 방법',goal:'목표',price:'가격 가설',validation:'실험 계획',revenue_model:'수익 모델',business_model:'사업 모델',risks:'주요 위험',plan:'실행 계획',summary:'초안 요약',customer:'대상 고객',target_customer:'대상 고객'};
function proposalText(value:unknown):string {
 if(value==null)return '';
 if(Array.isArray(value))return value.map(proposalText).join('\n');
 if(typeof value==='object')return Object.entries(value).map(([key,item])=>(proposalLabels[key]||key)+': '+proposalText(item)).join('\n');
 return String(value);
}
export function CompanyApprovals({items,pending,readOnly,decide}:{items:Venture[];pending:boolean;readOnly:boolean;decide:(id:string,approve:boolean)=>void}){
 return <>{items.map(item=>{
  let proposal:Record<string,unknown>;try{const value=JSON.parse(item.proposal_json);proposal=value&&typeof value==='object'&&!Array.isArray(value)?value:{summary:value}}catch{proposal={summary:item.proposal_json}}
  return <section key={item.id} aria-label={'사업안 승인: '+item.name} className="hermes-approval"><b>{item.name}</b><div className="space-y-3">{Object.entries(proposal).filter(([key])=>!['name','title'].includes(key)).map(([key,value])=><section key={key}><h4 className="text-sm font-semibold">{proposalLabels[key]||key.replaceAll('_',' ')}</h4><MessageBody text={key==='price'&&typeof value==='number'?value.toLocaleString('ko-KR')+'원 · 검증 전 가격 가설':proposalText(value)}/></section>)}</div><div className="hermes-actions"><Button tone="primary" disabled={pending||readOnly} title={readOnly?'읽기 모드를 끄면 승인 후 실행할 수 있습니다':undefined} onClick={()=>{if(window.confirm(item.name+' 사업안을 승인하고 승인 범위 내 자율 제작·운영을 시작할까요?\n외부 공개·결제·지출은 별도 승인이 필요합니다.'))decide(item.id,true)}}>사업 승인</Button><Button disabled={pending} onClick={()=>decide(item.id,false)}>보류</Button></div><p>수정할 내용은 총괄에게 편하게 말씀하세요. 승인 전에는 제품 제작·공개를 시작하지 않습니다.</p>{readOnly&&<p>읽기 모드에서는 사업 실행을 승인할 수 없습니다.</p>}</section>
 })}</>;
}
