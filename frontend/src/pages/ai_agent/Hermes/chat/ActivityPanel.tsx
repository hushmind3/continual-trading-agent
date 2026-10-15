import type {Ref} from 'react';
import {X,RefreshCw,Archive} from 'lucide-react';
import {Button} from '../../../../ui/Primitives';
import type {Job} from '../types';
import {ActivityTimeline} from './ChatStream';
interface Props{activityPanel:Ref<HTMLElement>;thisJob?:Job;selected:string;pending:boolean;active:boolean;onClose:()=>void;onRefresh:()=>void;archive:()=>void}
export function ActivityPanel({activityPanel,thisJob,selected,pending,active,onClose,onRefresh,archive}:Props){return <aside ref={activityPanel} className="hermes-log" aria-label="작업 내역"><header><div><h3>작업 내역</h3><p>도구 호출과 실제 결과</p></div><Button aria-label="작업 내역 닫기" onClick={onClose}><X size={18}/></Button></header><ActivityTimeline job={thisJob}/><div className="ha-log-footer"><Button aria-label="작업 상태 새로고침" onClick={onRefresh}><RefreshCw size={14}/>상태 갱신</Button><Button aria-label="현재 대화 보관" disabled={!selected||pending||(active&&!!thisJob)} onClick={()=>void archive()}><Archive size={14}/>대화 보관</Button></div></aside>;}
