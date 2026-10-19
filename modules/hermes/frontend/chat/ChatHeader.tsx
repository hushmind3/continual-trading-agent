import type {Ref} from 'react';
import {PanelLeft,ChevronDown} from 'lucide-react';
import {IconButton} from '@platform/ui/Primitives';
import type {Metrics} from '../types';
import {RuntimeMetrics} from './RuntimeMetrics';
import {HeaderActions} from './HeaderActions';
interface Props {
 sessionsOpen:boolean;sessionButton:Ref<HTMLButtonElement>;title:string;
 shownModel?:string;modelReady:boolean;modelState?:string;metrics?:Metrics;
 pending:boolean;create:()=>void;activityButton:Ref<HTMLButtonElement>;
 activityOpen:boolean;toggleActivity:()=>void;focused:boolean;onFocus:()=>void;
 onModels:()=>void;onSettings:()=>void;toggleSessions:()=>void;
 company?:{open:boolean;toggle:()=>void};
}
export function ChatHeader(props:Props){
 const {sessionsOpen,sessionButton,title,shownModel,modelReady,modelState,metrics,onModels,toggleSessions}=props;
 const state=modelReady?'실행 중':modelState==='loading'?'불러오는 중':modelState==='error'?'연결 오류':'미실행';
 return <header className="hermes-chat-heading">
  <IconButton ref={sessionButton} title="대화 기록" aria-label={sessionsOpen?'대화 기록 접기':'대화 기록 열기'} aria-expanded={sessionsOpen} aria-controls="hermes-session-sidebar" onClick={toggleSessions}><PanelLeft size={19}/></IconButton>
  <div className="hermes-chat-title"><h2>헤르메스</h2><p title={title}>{title}</p></div>
  <IconButton className="ha-model-chip" onClick={onModels} title={'사용 모델 · '+state+' · 모델 설정 열기'}>
   <span className={'ha-model-dot '+(modelReady?'ready':'')}/><span>{shownModel||'모델 선택'}</span><small className="ha-model-state">{state}</small><ChevronDown size={12}/>
  </IconButton>
  <RuntimeMetrics metrics={metrics}/>
  <HeaderActions {...props}/>
 </header>;
}
