import {useOperations} from '../data/Operations';
import {Status} from './Primitives';
import {date,number} from './format';
import {HelpDisclosure} from './HelpDisclosure';

const metrics:Record<string,Record<string,string>>={feed:{new_bars:'새 저장 봉',polls:'수집 조회'},experts:{inferences:'분석 완료',new_inputs:'새 입력 분석'},agent:{decisions:'새 판단',market_batches:'시장 결과 처리'},learner:{updates:'학습 가중치 조정'}};
const meanings:Record<string,string>={feed:'수집 조회는 서버에 확인한 횟수입니다. 새 저장 봉이 늘어야 새로운 완료 시세가 들어온 것입니다. 연결됨이나 응답 시각만으로 시세 진행을 판단하지 않습니다.',experts:'분석 완료는 실제 추론을 끝낸 횟수입니다. 새 입력 분석은 사용한 데이터 시각이 앞으로 바뀐 횟수입니다. 같은 입력 재분석은 새 판단·학습을 보장하지 않습니다.',agent:'새 판단은 중앙 모델이 새 시장 시각에서 비중을 계산한 횟수입니다. 시장 결과 처리는 계좌·주문 결과를 확인한 횟수이며, 판단과 체결은 서로 다른 단계입니다.',learner:'학습 가중치 조정은 optimizer가 실제 가중치를 바꾼 횟수입니다. 저장 버전은 Expert 선택·교체로도 바뀌므로 학습 횟수가 아닙니다.'};

export function ServiceProgress({role,showState=true}:{role:string;showState?:boolean}){
 const {state}=useOperations();const value=state?.progress?.[role];
 if(!value)return <p className="text-xs text-slate-400">실제 진행 계측 준비 중</p>;
 const tone=value.code==='progress'?'good':value.code==='error'||value.code==='unresponsive'?'bad':value.code==='waiting'?'warn':'neutral';
 return <div className="min-w-0 space-y-2 text-xs" data-testid={`progress-${role}`}>
  <div className="flex flex-wrap items-center gap-2"><span className="text-slate-500">{value.service_alive?'서비스 켜짐':'서비스 꺼짐'}</span>{showState&&<Status tone={tone}>{value.label}</Status>}</div>
  <div className="space-y-1 rounded-lg bg-slate-50 p-2"><p className="text-[11px] text-slate-400">최근 60초 · 현재 {value.observed_seconds}초 관찰</p>
   {Object.entries(metrics[role]).map(([key,label])=><p key={key} className="flex flex-wrap justify-between gap-2"><span>{label}</span><b className={(value.changes[key]??0)>0?'text-emerald-700':'text-slate-500'}>{value.changes[key]==null?'계측 준비':`+${number(value.changes[key],0)}`}{value.counters[key]!=null?` / ${number(value.counters[key],0)}`:''}</b></p>)}
  </div>
  <p className="text-slate-500">마지막 실제 완료: {value.last_completed_at?date(value.last_completed_at):'완료 시각 기록 없음'}</p>
  {value.source_as_of&&<p className="text-slate-500">사용 데이터: {date(value.source_as_of)}</p>}
  <HelpDisclosure title="진행 표시 기준"><p>{meanings[role]}</p><p>왼쪽 +숫자는 관찰 기간 증가량, 오른쪽 숫자는 해당 카운터의 누적값입니다. 프로세스 재시작·구성 변경 시 관찰 기준을 다시 잡습니다.</p><p>서비스 응답: {date(value.heartbeat_at??undefined)}</p>{value.detail&&<p>현재 이유: {value.detail}</p>}</HelpDisclosure>
 </div>;
}
