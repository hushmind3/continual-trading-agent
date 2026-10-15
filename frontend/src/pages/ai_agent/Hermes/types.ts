export const prefix='ai_agent/Hermes/';
export interface Session {id:string;title?:string;model?:string;updated_at?:number;created_at?:number}
export interface Message {role:string;content:unknown;tool_calls?:unknown[];name?:string}
export interface SessionDetail {session:Session;messages:Message[]}
export interface Settings {base_url:string;model:string;api_key:string;has_api_key:boolean;workspace:string;max_iterations:number;toolsets:string[];local_model:string;python:string;engine:string;available_toolsets:string[];computer_driver_installed:boolean}
export interface Job {state:string;session_id:string|null;text:string;error:string;events:{name:string;detail:string;time:number}[];started_at?:number;approval?:{kind:'tool'|'question';detail:string}}
export interface AgentStatus {job:Job;local_model:{running:boolean;base_url:string;state?:string;error?:string}}
export const working=(s?:AgentStatus)=>!!s&&['starting','running','stopping'].includes(s.job.state);
export function failure(e:unknown){return e instanceof Error?e.message:String(e)}
export function contentText(value:unknown):string {
 if(typeof value==='string')return value;
 if(Array.isArray(value))return value.map(v=>typeof v==='object'&&v!==null&&'text' in v?String(v.text):'').filter(Boolean).join('\n');
 return value==null?'':JSON.stringify(value,null,2);
}
