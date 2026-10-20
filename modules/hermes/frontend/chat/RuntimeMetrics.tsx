import type {Metrics} from '../types';
const number=(value?:number)=>value==null?'—':value.toLocaleString('ko-KR');
interface Props {metrics?:Metrics}
export function RuntimeMetrics({metrics:m}:Props){
 const percent=m?.context_limit&&m.context_tokens!=null?Math.min(100,m.context_tokens/m.context_limit*100):undefined;
 const facts=[
  {label:'컨텍스트',value:number(m?.context_tokens),suffix:' / '+number(m?.context_limit),note:(percent==null?'실행기 보고값':percent.toFixed(1)+'% 사용')+' · 이전 대화·지침·도구 결과를 포함한 문맥입니다. 이번 메시지만의 토큰 수가 아닙니다.',known:m?.context_tokens!=null},
  {label:'생성 속도',value:m?.generation_tps==null?'—':m.generation_tps+' tok/s',note:'최근 측정 구간의 생성 속도',known:m?.generation_tps!=null},
  {label:'입력 토큰',value:number(m?.input_tokens),note:'현재 작업의 누적 입력 토큰',known:m?.input_tokens!=null},
  {label:'출력 토큰',value:number(m?.output_tokens),note:'현재 작업의 누적 출력 토큰',known:m?.output_tokens!=null},
  {label:'모델 요청',value:m?.api_calls==null?'—':number(m.api_calls)+'회',note:'현재 작업의 모델 요청 횟수',known:m?.api_calls!=null},
  {label:'전체 작업',value:m?.elapsed_seconds==null?'—':Math.round(m.elapsed_seconds)+'초',note:'모든 모델 요청·검색·도구 실행·대기를 합한 시간입니다. API 한 번의 응답 시간이 아닙니다.',known:m?.elapsed_seconds!=null},
 ];
 return <dl className="hermes-runtime-metrics" aria-label="모델 실행 정보">
  {facts.map(fact=><div key={fact.label} title={fact.note} className={fact.known?'is-measured':'is-unmeasured'}>
   <dt>{fact.label}</dt><dd>{fact.value}{fact.suffix&&<span>{fact.suffix}</span>}</dd>
  </div>)}
 </dl>;
}
