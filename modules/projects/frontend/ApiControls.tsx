import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Input,Select,ErrorMessage} from '@platform/ui/Primitives';
type Schema={$ref?:string;type?:string;title?:string;description?:string;default?:unknown;enum?:unknown[];properties?:Record<string,Schema>;required?:string[]};
type Parameter={name:string;in:string;required?:boolean;schema:Schema};
type Operation={summary?:string;operationId?:string;parameters?:Parameter[];requestBody?:{content?:Record<string,{schema:Schema}>}};
type Specification={paths:Record<string,Record<string,Operation>>;components?:{schemas?:Record<string,Schema>}};
type Field={name:string;place:string;required?:boolean;schema:Schema};
const decode=(body:string)=>new TextDecoder().decode(Uint8Array.from(atob(body),c=>c.charCodeAt(0)));
export function ApiControls({projectId}:{projectId:string}){
 const [spec,setSpec]=useState<Specification|null>(null),[selected,setSelected]=useState(''),[values,setValues]=useState<Record<string,string>>({}),[text,setText]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{let active=true;request<{body:string;status:number}>('projects/invoke',{id:projectId,path:'/openapi.json',method:'GET'}).then(response=>{if(response.status!==200)throw Error('프로젝트 기능 목록을 읽지 못했습니다.');const parsed=JSON.parse(decode(response.body)) as Specification;if(active)setSpec(parsed)}).catch(e=>{if(active)setError(String(e))});return()=>{active=false}},[projectId]);
 const operations=Object.entries(spec?.paths||{}).flatMap(([path,methods])=>Object.entries(methods).filter(([method])=>['get','post','put','patch','delete'].includes(method)).map(([method,operation])=>({path,method,operation,key:method+' '+path})));
 const current=operations.find(item=>item.key===(selected||operations[0]?.key));
 function resolve(schema:Schema):Schema{for(let i=0;schema.$ref&&i<4;i++)schema=spec?.components?.schemas?.[schema.$ref.split('/').at(-1)||'']||{};return schema}
 const body=resolve(current?.operation.requestBody?.content?.['application/json']?.schema||{});
 const fields:Field[]=[...(current?.operation.parameters||[]).filter(item=>['path','query'].includes(item.in)).map(item=>({name:item.name,place:item.in,required:item.required,schema:resolve(item.schema)})),...Object.entries(body.properties||{}).map(([name,schema])=>({name,place:'body',schema:resolve(schema),required:body.required?.includes(name)}))];
 async function execute(){if(!current)return;setBusy(true);setError('');try{
  let path=current.path;const query=new URLSearchParams(),payload:Record<string,unknown>={};
  for(const field of fields){const raw=values[field.place+'.'+field.name]??String(field.schema.default??'');if(raw===''&&!field.required)continue;if(raw===''&&field.required)throw Error((field.schema.title||field.name)+' 항목을 입력하세요.');let value:unknown=raw;
   if(['number','integer'].includes(field.schema.type||'')){value=Number(raw);if(!Number.isFinite(value))throw Error('숫자를 입력하세요: '+field.name)}
   if(field.schema.type==='boolean')value=raw==='true';if(['object','array'].includes(field.schema.type||''))value=JSON.parse(raw);
   if(field.place==='path')path=path.replace('{'+field.name+'}',encodeURIComponent(String(value)));else if(field.place==='query')query.set(field.name,String(value));else payload[field.name]=value;
  }
  const response=await request<{status:number;body:string}>('projects/invoke',{id:projectId,path,query:query.toString(),method:current.method.toUpperCase(),headers:{'content-type':'application/json'},body:current.method==='get'?'':JSON.stringify(payload)});
  const decoded=decode(response.body);try{setText(JSON.stringify(JSON.parse(decoded),null,2))}catch{setText(decoded)}if(response.status>=400)setError('프로젝트 실행 응답: HTTP '+response.status);
 }catch(e){setError(String(e))}finally{setBusy(false)}}
 return <div className="space-y-4"><ErrorMessage message={error}/><label className="block space-y-2 text-sm font-medium"><span>실행할 기능</span><Select aria-label="실행할 기능" value={selected||operations[0]?.key||''} onChange={e=>{setSelected(e.target.value);setValues({});setText('')}}>{operations.map(item=><option key={item.key} value={item.key}>{item.operation.summary||item.operation.operationId||item.path}</option>)}</Select></label>
 <div className="grid gap-4 sm:grid-cols-2">{fields.map(field=><label key={field.place+'.'+field.name} className="space-y-2 text-sm"><span>{field.schema.title||field.name}{field.required?' *':''}</span>{field.schema.type==='boolean'||field.schema.enum?<Select aria-label={field.name} value={values[field.place+'.'+field.name]??String(field.schema.default??'')} onChange={e=>setValues({...values,[field.place+'.'+field.name]:e.target.value})}><option value="">선택하세요</option>{(field.schema.enum||[true,false]).map(value=><option key={String(value)} value={String(value)}>{String(value)}</option>)}</Select>:<Input aria-label={field.name} placeholder={field.schema.description||''} value={values[field.place+'.'+field.name]??String(field.schema.default??'')} onChange={e=>setValues({...values,[field.place+'.'+field.name]:e.target.value})}/>}</label>)}</div>
 <Button tone="primary" busy={busy} disabled={!current} onClick={()=>void execute()}>실행</Button>{text&&<pre className="max-h-screen overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-4 text-sm">{text}</pre>}
 </div>;
}
