export const prefix='ai_agent/Hermes/';
export interface Session {managed?:boolean;id:string;title?:string;model?:string;updated_at?:number;created_at?:number}
export interface Message {display_kind?:string;role:string;content:unknown;tool_calls?:unknown[];tool_call_id?:string;name?:string}
export interface SessionDetail {session:Session;messages:Message[]}
export interface Settings {provider?:'custom'|'openai-codex';base_url:string;model:string;api_key:string;has_api_key:boolean;workspace:string;max_iterations:number;toolsets:string[];local_model:string;system_prompt?:string;agent_prompts?:Record<string,string>;agent_prompt_profiles?:{id:string;name:string;default_prompt:string}[];read_only?:boolean;context_length?:number;max_output_tokens?:number;thinking_mode?:'auto'|'on'|'off';reasoning_effort?:string;tool_loading?:'native'|'lazy'|'eager';python:string;engine:string;available_toolsets:string[];toolset_options?:{id:string;description:string}[];computer_driver_installed:boolean;browser_runtime_installed?:boolean}
export interface AutonomousState {mode:string;status:string;goal?:string;prompt?:string;turns_used?:number;max_turns?:number;ticks_fired?:number;times?:number;paused_reason?:string;last_stop_reason?:string;last_reason?:string;next_due_at?:number}
export interface Job {meeting?:MeetingLive;can_steer?:boolean;application?:boolean;metrics?:Metrics;live_text?:string;phase?:string;autonomy?:AutonomousState;state:string;session_id:string|null;text:string;error:string;events:{name:string;detail:string;time:number}[];started_at?:number;approval?:{kind:'tool'|'question';detail:string}}
export interface AgentStatus {model_connection?:{provider:string;state:string};job:Job;local_model:{running:boolean;base_url:string;state?:string;error?:string}}
export const working=(s?:AgentStatus)=>!!s&&['starting','running','stopping'].includes(s.job.state);
export function failure(e:unknown){return e instanceof Error?e.message:String(e)}
export function contentText(value:unknown):string {
 if(typeof value==='string')return value;
 if(Array.isArray(value))return value.map(v=>typeof v==='object'&&v!==null&&'text' in v?String(v.text):'').filter(Boolean).join('\n');
 return value==null?'':JSON.stringify(value,null,2);
}

export interface Metrics {context_limit?:number;context_tokens?:number;generation_tps?:number;input_tokens?:number;output_tokens?:number;api_calls?:number;elapsed_seconds?:number}

export interface MeetingLive {run_id?:string;id:string;company_id:string;topic:string;status:string;role?:string;turn_id?:string;turn_status?:string;text?:string;source_session_id?:string;venture_id?:string;error?:string}
