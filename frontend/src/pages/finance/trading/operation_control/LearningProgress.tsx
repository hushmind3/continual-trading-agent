import {useOperations} from '../../../../data/Operations';
import {Panel,KeyValues} from '../../../../ui/Panel';
import {ErrorMessage} from '../../../../ui/Primitives';
import {money,number,date} from '../../../../ui/format';

export function LearningProgress(){
 const {state}=useOperations(),operation=state?.operations,learning=operation?.learning;
 if(!operation)return null;
 const current=learning?.current,completed=learning?.last_completed,applied=learning?.last_applied;
 return <Panel title="운영 모델 · 학습 상태" description="수신 시세, 실제 학습 완료, 운영 반영, 가상계좌 성과를 각각 확인합니다.">
  <div className="mb-4 grid gap-3 sm:grid-cols-2">{(['KRW','USD'] as const).map(currency=>{
   const policy=operation.policies?.[currency],saved=state?.checkpoints.find(item=>item.path===policy?.path);
   const input=saved?.identity.training_input as {consumed_end?:string;end?:string}|undefined;
   return <section key={currency} className="rounded-xl border border-slate-200 p-3"><h3 className="text-xs font-semibold">{currency} 운영 모델</h3>
    {policy?<><p className="mt-2 break-all text-sm font-semibold">{saved?.name??policy.path}</p><p className="mt-1 text-xs text-slate-500">{policy.loaded?'메모리 로드됨 · '+policy.device:'선택됨 · 메모리 미로드'} · {number(saved?.num_timesteps,0)} 학습 단계 · {number(saved?.updates,0)} 업데이트</p><p className="mt-2 text-xs text-slate-500">실제 학습 마지막 봉: {input?.consumed_end??'기록 없음'}</p><p className="mt-1 text-xs text-slate-500">입력 최신 봉: {input?.end??'기록 없음'}</p></>:<p className="mt-2 text-xs text-amber-700">승인한 모델이 없습니다. 정책 학습 화면에서 이 통화의 저장 모델을 로드하세요.</p>}
   </section>;
  })}</div>
  <div className="learning-current-summary"><KeyValues items={[['시세 수신',operation.feed.last_as_of?date(operation.feed.last_as_of):'수신 기록 없음'],['지속 학습',operation.controls.learning?learning?.status??operation.feed.learning_status??'입력 대기':'꺼짐']]}/></div><details className="learning-measurements"><summary>학습 상세 기록</summary><KeyValues items={[
   ['시세 수신',operation.feed.last_as_of?date(operation.feed.last_as_of):'수신 기록 없음'],
   ['지속학습',operation.controls.learning?learning?.status??operation.feed.learning_status??'입력 대기':'꺼짐'],
   ['학습 입력',current?.input?`${current.input.timeframe} · ${number(current.input.observations,0)}행 · ${current.input.end}`:'새 입력 대기'],
   ['이번 입력의 학습 대기 봉',current?.input.pending_observations!=null?number(current.input.pending_observations,0):'작업 시작 후 표시'],
   ['이번 학습 작업량',current?.input.requested_timesteps!=null?number(current.input.requested_timesteps,0)+'단계':'작업 시작 후 표시'],
   ['작업 시간 추정',current?.input.target_seconds!=null?`목표 ${number(current.input.target_seconds,1)}초 · 예상 ${current.input.estimated_seconds!=null?number(current.input.estimated_seconds,1)+'초':'속도 기록 없음'}`:'작업 시작 후 표시'],
   ['직전 실제 학습 시각',current?.input.consumed_end?date(current.input.consumed_end):'소비 범위 기록 없음'],
   ['완료된 학습',completed?`${completed.currency} · ${number(completed.num_timesteps,0)}단계 · 업데이트 ${number(completed.updates,0)}`:'완료 기록 없음'],
   ['실제로 학습한 마지막 시각',completed?.consumed_end?date(completed.consumed_end):'소비 범위 기록 없음'],
   ['운영 반영',applied?`${applied.currency} · ${applied.path}`:'반영 기록 없음'],
  ]}/></details>
  <ErrorMessage message={learning?.error??operation.feed.learning_error??''}/>
  {current?.input.rollout_exceeds_target&&<p className="mt-3 text-xs text-amber-700">이 알고리즘의 공식 rollout 단위가 시간 목표보다 큽니다. 기본값을 유지하므로 작업이 더 오래 걸릴 수 있습니다.</p>}
  <div className="mt-4 grid gap-3 sm:grid-cols-2">{(['USD','KRW'] as const).map(currency=>{
   const book=operation.account.books[currency],rate=book.initial_cash>0?(book.equity/book.initial_cash-1)*100:null;
   return <div key={currency} className="rounded-xl bg-slate-50 p-3"><h3 className="mb-2 text-xs font-semibold">{currency} 가상운영 성과</h3><p className="text-sm font-semibold">초기자금 대비 {rate==null?'미측정':number(rate,2)+'%'}</p><p className="mt-2 text-xs text-slate-600">순손익 {money(book.net_pnl,currency)} · 수수료 {money(book.fees,currency)} · 체결 {number(book.trade_count,0)}건</p></div>;
  })}</div>
  <p className="mt-3 text-xs text-slate-500">학습 단계·업데이트 횟수는 수익 개선의 증거가 아닙니다. 위 수익률은 기록된 가상계좌 평가액이며 실제 증권사 주문을 전송하지 않습니다.</p>
 </Panel>;
}
