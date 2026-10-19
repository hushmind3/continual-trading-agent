export interface Message {id:string;seq:number;speaker:string;body:string;created_at:string}
export interface Meeting {id:string;topic:string;status:string;summary:string;created_at:string;venture_id:string;minutes:{role:string;name:string;statement:string}[]}
export interface Job {id:string;role:string;type:string;title:string;status:string;result:string;error:string;mode:string;created_at:string;started_at?:string;finished_at?:string}
export interface Role {role:string;name:string;title:string;description:string;status:string;queued:number;running:number;completed:number;failed:number;latest?:{title:string;status:string}}
export interface Venture {id:string;name:string;status:string;mode:string;proposal:Record<string,string|number>}
export interface WorkspaceData {plan_preparing?:string[];plans?:ExecutionPlan[];ceo:{messages:Message[]};team:{roles:Role[]};meetings:Meeting[];jobs:Job[];ventures:Venture[];include_engine_context:boolean;active_product?:{name:string}|null;requests:{id:string;status:string;error:string;elapsed_seconds:number}[]}
export interface Harness {state?:string;error?:string;phase?:{kind:string;role:string;label:string;started_at:number}}
export const roles=['CPO','CTO','CMO','CFO','QA','CEO'];
export const statusNames:Record<string,string>={running:'진행 중',working:'진행 중',queued:'대기',blocked:'선행 작업 대기',completed:'완료',failed:'실패',idle:'배정 없음',pending:'승인 대기',approved:'승인됨',rejected:'보류됨'};

export interface ExecutionPlan {report_message_id:string;meeting_id:string;status:string;summary:string;tasks:{phase:string;role:string;title:string;brief:string;deliverable:string;acceptance:string}[];jobs:{id:string;role:string;title:string;status:string;error?:string}[]}
