import type {Metrics} from '../types';
const number=(value?:number)=>value==null?'—':value.toLocaleString('ko-KR');
interface Props {metrics?:Metrics}
export function RuntimeMetrics({metrics:m}:Props){
 const percent=m?.context_limit&&m.context_tokens!=null?Math.min(100,m.context_tokens/m.context_limit*100):undefined;
 const delta=m?.context_tokens!=null&&m.previous_context_tokens!=null?m.context_tokens-m.previous_context_tokens:undefined;
 const facts=[
  {label:'컨텍스트',value:number(m?.context_tokens),suffix:' / '+number(m?.context_limit),note:(percent==null?'실행기 보고값':percent.toFixed(1)+'% 사용')+' · 이전 대화·지침·도구 결과를 포함한 문맥입니다. 이번 메시지만의 토큰 수가 아닙니다.',known:m?.context_tokens!=null},
  {label:'문맥 증감',value:delta==null?'—':(delta>0?'+':'')+number(delta),note:'직전 완료 작업의 문맥과 비교한 증감입니다. 압축·도구·출력도 반영되며 새로 처리한 입력 토큰과 다릅니다.',known:delta!=null},
  {label:'생성 속도',value:m?.generation_tps==null?'—':m.generation_tps+' tok/s',note:'최근 측정 구간의 생성 속도',known:m?.generation_tps!=null},
  {label:m?.request_input_tokens==null&&m?.input_tokens!=null?'이전 집계 입력':m?.recorded_at?'최근 입력':'이번 입력',value:number(m?.request_input_tokens??m?.input_tokens),note:m?.request_input_tokens==null?'이전 방식으로 저장한 입력 집계입니다. 당시 전체 입력·캐시 구분은 저장되지 않았습니다.':'이번 작업의 모든 모델 요청에 보낸 입력 합계입니다. 반복 전송한 문맥과 캐시 재사용도 포함합니다.',known:m?.request_input_tokens!=null||m?.input_tokens!=null},
  {label:'캐시 재사용',value:m?.cached_input_tokens==null?'미확인':number(m.cached_input_tokens),note:'모델 제공자 또는 로컬 실행기가 실제 보고한 재사용 입력입니다. 미보고 값을 0으로 추정하지 않습니다.',known:m?.cached_input_tokens!=null},
  {label:'새 입력 처리',value:m?.processed_input_tokens==null?'미확인':number(m.processed_input_tokens),note:'캐시 재사용을 제외하고 이번 작업에서 처리한 입력입니다. 새로 친 글자 수와 다릅니다.',known:m?.processed_input_tokens!=null},
  {label:'대화 누적 입력',value:number(m?.cumulative_input_tokens),note:'최근 완료 시점에 기존 Choki DB에 집계된 세션 누적 입력입니다. 캐시 입력도 포함합니다.',known:m?.cumulative_input_tokens!=null},
  {label:'출력 토큰',value:number(m?.output_tokens),note:'현재 작업의 누적 출력 토큰',known:m?.output_tokens!=null},
  {label:'모델 요청',value:m?.api_calls==null?'—':number(m.api_calls)+'회',note:'현재 작업의 모델 요청 횟수',known:m?.api_calls!=null},
  {label:'전체 작업',value:m?.elapsed_seconds==null?'—':Math.round(m.elapsed_seconds)+'초',note:'모든 모델 요청·검색·도구 실행·대기를 합한 시간입니다. API 한 번의 응답 시간이 아닙니다.',known:m?.elapsed_seconds!=null},
 ];
 return <dl className="hermes-runtime-metrics" aria-label={m?.recorded_at?'최근 완료 작업의 모델 실행 정보':'현재 작업의 모델 실행 정보'}>
  {facts.map(fact=><div key={fact.label} title={fact.note} className={fact.known?'is-measured':'is-unmeasured'}>
   <dt>{fact.label}</dt><dd>{fact.value}{fact.suffix&&<span>{fact.suffix}</span>}</dd>
  </div>)}
 </dl>;
}
