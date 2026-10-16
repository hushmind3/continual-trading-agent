import {EngineNotes} from './EngineNotes';
import type {Ref} from 'react';
import {X,RefreshCw} from 'lucide-react';
import {Button} from '../../../../ui/Primitives';
import type {Job,Message} from '../types';
import {ActivityTimeline,CurrentActivity,ToolHistory} from './ChatStream';
interface Props{messages:Message[];activityPanel:Ref<HTMLElement>;thisJob?:Job;selected:string;pending:boolean;active:boolean;onClose:()=>void;onRefresh:()=>void;archive:()=>void}
export function ActivityPanel({messages,activityPanel,thisJob,active,onClose,onRefresh}:Props){const count=messages.reduce((total,message)=>total+(message.tool_calls?.length??0),0);return <aside ref={activityPanel} className="hermes-log" aria-label="작업 내역"><header><div><h3>작업 내역 <small>{count}단계</small></h3></div><div className="ha-activity-actions"><Button aria-label="작업 상태 새로고침" title="작업 상태 새로고침" onClick={onRefresh}><RefreshCw size={15}/></Button><Button aria-label="작업 내역 닫기" title="닫기" onClick={onClose}><X size={18}/></Button></div></header><EngineNotes messages={messages}/><CurrentActivity job={thisJob} active={active}/>{thisJob?.events.length?<ActivityTimeline job={thisJob}/>:<ToolHistory messages={messages}/>}</aside>;}
