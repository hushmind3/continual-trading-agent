import {useOperations} from '../data/Operations';
import {Status} from './Primitives';
const labels:Record<string,string>={starting:'시작 준비',running:'실행 중',succeeded:'완료',failed:'실패',stopped:'중단',unknown:'완료 기록 없음',connected:'연결됨',disconnected:'연결 끊김',connecting:'연결 중',reconnecting:'재연결 중',streaming:'시세 수신 중',waiting:'입력 대기',idle:'대기',pending:'대기',blocked:'진행 불가',disabled:'꺼짐'};
export function ServiceProgress({role}:{role:'learner'|'experts'|'feed'|'agent'}){const {state}=useOperations();if(!state)return null;
  if(role==='feed')return <div className="space-y-1"><Status tone={state.operations?.feed.error?'bad':state.operations?.controls.feed?'good':'idle'}>{labels[state.operations?.feed.status||'']||state.operations?.feed.status||'수신 대기'}</Status><p className="text-xs text-slate-400">{state.operations?.feed.error||state.operations?.feed.last_as_of||'수신 기록 없음'}</p></div>;
  if(role==='experts'){const job=state.library?.job;return <div className="space-y-1"><Status tone={job?.busy?'good':job?.stage==='error'?'bad':job?.stage==='partial'?'warn':'idle'}>{job?.busy?'모델 작업 실행 중':job?.stage==='partial'?'일부 실패 / 입력 미충족':job?.stage==='complete'?'모델 작업 완료':'모델 작업 대기'}</Status><p className="text-xs text-slate-400">{job?.detail??job?.error??('사용 선택 '+state.experts.active.length+'개')}{job?.busy&&job.total?' · '+(job.completed??0)+'/'+job.total:''}</p></div>}
  if(role==='agent')return <Status tone={state.model.compatible?'good':'warn'}>{state.model.compatible?'선택 정책 호환':'정책 미생성 / 이전 환경'}</Status>;
  return <Status tone={state.job.status==='failed'?'bad':state.job.running?'good':'idle'}>{labels[state.job.status||'']||'실행 대기'}</Status>;
}
