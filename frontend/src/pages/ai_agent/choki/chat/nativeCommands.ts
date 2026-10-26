import {GatewayClient} from '@hermes-official/lib/gatewayClient';
import {contentText} from '../types';
import {stripAnsi} from '@hermes/shared';
import '../settings/official/transport';

export interface CommandCatalog {
 pairs:[string,string][];canon:Record<string,string>;
 commands:Record<string,{argument_mode?:string|null;desktop?:string|null}>;
 categories?:{name:string;pairs:[string,string][]}[];sub:Record<string,string[]>;skills:Record<string,unknown>;warning?:string;
}
export interface CommandResult {output?:string;warning?:string;type?:string;message?:string;display?:string;target?:string;session_id?:string;task_id?:string;status?:string;download?:{filename:string;content:string;format:string}}
interface NativeMessage {role?:string;row_id?:number;content?:unknown;display_kind?:string;archived?:boolean}
interface NativeSession {session_id:string;subscription_id:string;session_key?:string;stored_session_id?:string;revision:number;execution_generation:number;info?:{title?:string};messages?:NativeMessage[];stored_messages?:NativeMessage[]}
const gateway=new GatewayClient();
let opening:Promise<void>|undefined;
async function connected(){
 if(gateway.connectionState!=='open'){opening??=gateway.connect().finally(()=>{opening=undefined});await opening}
 return gateway;
}
export async function commandCatalog(){
 const client=await connected(),catalog=await client.request<CommandCatalog>('commands.catalog',{});
 // The completion list omits messaging-only commands; resolve the complete registered metadata too.
 const listed=new Set(catalog.pairs.map(([key])=>key));
 const missing=Object.keys(catalog.commands).filter(key=>!catalog.canon[key]&&!listed.has(key));
 const resolved=await Promise.all(missing.map(async name=>({name,result:await client.request<{canonical:string;description:string;category:string}>('command.resolve',{name})})));
 for(const {name,result} of resolved){
  const canonical='/'+result.canonical.replace(/^\//,'');catalog.canon[name]=canonical;
  if(!listed.has(canonical)){catalog.pairs.push([canonical,result.description]);listed.add(canonical)}
  catalog.commands[canonical]??=catalog.commands[name];
 }
 return catalog;
}
/** Resume the actual stored conversation; runtime IDs never replace its persistent ID. */
export async function executeCommand(stored:string,command:string):Promise<CommandResult>{
 const client=await connected();
 const [typed,...parts]=command.trim().split(/\s+/),arg=parts.join(' ');
 const resolved=await client.request<{canonical:string}>('command.resolve',{name:typed});
 const name='/'+resolved.canonical.replace(/^\//,'');
 const reference=name==='/resume'&&arg?arg:stored;
 const session=reference
  ?await client.request<NativeSession>('session.resume',{session_id:reference,omit_messages:!['/undo','/retry','/history'].includes(name),source:'gui'})
  :await client.request<NativeSession>('session.create',{source:'gui'});
 const mutate=(operation:string,payload:Record<string,unknown>,snapshot=session)=>client.request<Record<string,unknown>>('session.mutate',{session_id:session.session_id,request_id:crypto.randomUUID(),expected_revision:snapshot.revision,expected_generation:snapshot.execution_generation,operation,payload});
 let keep=false;
 try{
  const id=session.session_id;
  let result:CommandResult;
  if(name==='/resume'&&arg){
   result={type:'select',session_id:session.stored_session_id||session.session_id,output:'선택한 대화를 이어갑니다.'};
  }else if(name==='/branch'){
   const receipt=await mutate('branch',arg?{title:arg}:{});
   if(typeof receipt.branched_session_id!=='string')throw new Error('공식 실행기에서 분기된 대화 ID를 반환하지 않았습니다.');
   result={type:'select',session_id:receipt.branched_session_id,output:'현재 대화 기록에서 새 대화를 분기했습니다.'};
  }else if(name==='/history'){
   const count=arg?Number(arg):20;
   if(!Number.isInteger(count)||count<1)throw new Error('표시할 메시지 수를 양의 정수로 입력하세요.');
   const roles:Record<string,string>={user:'사용자',assistant:'답변',tool:'도구'};
   result={output:(session.messages||[]).filter(row=>row.role&&row.role in roles).slice(-count).map(row=>roles[row.role!]+'\n'+contentText(row.content)).join('\n\n')||'저장된 대화가 없습니다.'};
  }else if(name==='/tools'){
   const info=await client.request<{tools?:unknown[];enabled_toolsets?:string[]}>('session.info',{session_id:id});
   result={output:JSON.stringify({tools:info.tools,toolsets:info.enabled_toolsets},null,2)};
  }else if(name==='/reload-skills'){
   result=await client.request<CommandResult>('skills.reload',{session_id:id});
  }else if(['/undo','/retry'].includes(name)){
   const count=arg?Number(arg):1;
   if(!Number.isInteger(count)||count<1)throw new Error('되돌릴 사용자 메시지 수를 양의 정수로 입력하세요.');
   // Match the original canonical client's live human-turn boundary, never its archived compaction rows.
   const target=(session.stored_messages??session.messages)?.filter(row=>row.role==='user'&&(!row.display_kind||row.display_kind==='steer')&&!row.archived&&Number.isSafeInteger(row.row_id)&&!(typeof row.content==='string'&&['[CONTEXT COMPACTION','[CONTEXT SUMMARY]:','[END OF PRIOR CONTEXT'].some(marker=>row.content!.toString().includes(marker)))).at(-count);
   if(!target?.row_id)throw new Error('되돌릴 사용자 메시지가 없습니다.');
   const content=target.content;
   if(typeof content!=='string'&&(!Array.isArray(content)||!content.every(part=>part&&['text','input_text','output_text'].includes(part.type)&&typeof part.text==='string'&&Object.keys(part).length===2)))throw new Error('첨부가 포함된 메시지는 대화에서 해당 메시지를 확인하고 다시 보내세요.');
   const receipt=await mutate('rewind',{target_message_id:target.row_id});
   result={type:name==='/retry'?'send':'prefill',message:contentText(content),output:'이전 사용자 메시지로 되돌렸습니다.',status:typeof receipt.status==='string'?receipt.status:undefined};
  }else if(name==='/compress'||name==='/compact'){
   const response=await mutate('compress',arg?{focus:arg}:{});
   keep=response.status==='pending';result={output:JSON.stringify(response,null,2),status:String(response.status||'')};
  }else if(name==='/title'){
   const response=arg?await mutate('rename',{title:arg}):{title:session.info?.title};result={output:String(response.title||'제목 없음')};
  }else if(name==='/rollback'){
   const words=parts.filter(part=>part!=='--all'),all=parts.includes('--all');
   const first=words[0]||'list';
   if(['list','ls','diff'].includes(first)&&(all||words.length>(first==='diff'?2:1)||first==='diff'&&!words[1]))throw new Error('사용법: /rollback list 또는 /rollback diff 변경번호 또는 /rollback 변경번호 [파일 경로] [--all]');
   const method=['list','ls'].includes(first)?'rollback.list':first==='diff'?'rollback.diff':'rollback.restore';
   const response=await client.request<Record<string,unknown>>(method,{session_id:id,...(method==='rollback.list'?{}:{hash:first==='diff'?words[1]:first}),...(method==='rollback.restore'?{...(words.length>1?{file_path:words.slice(1).join(' ')}:{}),...(all?{all:true}:{})}:{})});
   if(response.success===false||response.error)throw new Error(String(response.error||response.reason||'복원하지 못했습니다.'));
   result={output:JSON.stringify(response,null,2)};
  }else if(name==='/agents'||name==='/tasks'){
   const [agents,processes]=await Promise.all([client.request('subagent.list',{session_id:id}),client.request('process.list',{session_id:id})]);result={output:JSON.stringify({agents,processes},null,2)};
  }else if(name==='/config'){
   const response=await client.request('config.get',{session_id:id,key:arg||'full'});result={output:JSON.stringify(response,null,2)};
  }else if(name==='/save'){
   const words=[...parts],redact=['redact','--redact'].includes(words.at(-1)||'');if(redact)words.pop();
   const formats:Record<string,string>={json:'json',snapshot:'json',md:'md',markdown:'md',html:'html'},format=formats[words[0]||'json'];
   if(!format||words.length>2)throw new Error('사용법: /save [json|md|html] [파일명] [--redact]');
   const response=await client.request<{filename:string;content:string;format:string}>('session.export',{session_id:id,format,...(redact?{redact:true}:{})});
   result={type:'download',download:{...response,filename:words[1]||response.filename},output:'대화 파일을 내려받습니다.'};
  }else result=await client.request<CommandResult>('slash.exec',{session_id:session.session_id,command:name+(arg?' '+arg:'')});
  for(let aliases=0;result.type==='alias';aliases++){
   if(aliases>=8)throw new Error('명령 별칭이 반복되고 있습니다. 설정을 확인하세요.');
   result=await client.request<CommandResult>('slash.exec',{session_id:session.session_id,command:result.target||''});
  }
  return {...result,output:result.output?stripAnsi(result.output):undefined,session_id:result.session_id||session.stored_session_id||session.session_key||stored||session.session_id};
 }finally{
  // Read the persisted transcript again on the next command, including intervening platform turns.
  // A native command that started a live turn retains the official runtime instead of being stopped.
  if(!keep&&session.subscription_id)await client.request('session.detach',{session_id:session.session_id,subscription_id:session.subscription_id});
 }
}
