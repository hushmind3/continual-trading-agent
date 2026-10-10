import {useOperations} from '../data/Operations';
import {Status} from './Primitives';
const labels:Record<string,string>={starting:'시작 준비',running:'실행 중',succeeded:'완료',failed:'실패',stopped:'중단',unknown:'완료 기록 없음'};
export function ServiceProgress({role}:{role:'learner'|'experts'|'feed'|'agent'}){const {state}=useOperations();if(!state)return null;
  if(role==='feed')return <Status tone={state.data.error?'bad':'good'}>{state.data.error?'DB 조회 실패':'저장 가격 '+state.data.tickers+'종목'}</Status>;
  if(role==='experts')return <div className="space-y-1"><Status tone="idle">동결 Expert {state.experts.active.length}개 선택</Status><p className="text-xs text-slate-400">최근 출력: {state.experts.as_of||'기록 없음'}</p></div>;
  if(role==='agent')return <Status tone={state.model.compatible?'good':'warn'}>{state.model.compatible?'SAC 정책 호환':'정책 미생성 / 이전 환경'}</Status>;
  return <Status tone={state.job.status==='failed'?'bad':state.job.running?'good':'idle'}>{labels[state.job.status||'']||'실행 대기'}</Status>;
}
