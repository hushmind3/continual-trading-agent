import type {Metrics} from '../types';
const number=(value?:number)=>value==null?'—':value.toLocaleString('ko-KR');
interface Props {metrics?:Metrics}
export function RuntimeMetrics({metrics:m}:Props){
 const percent=m?.context_limit&&m.context_tokens!=null?Math.min(100,m.context_tokens/m.context_limit*100):undefined;
 const facts=[
  {label:'컨텍스트',value:number(m?.context_tokens),suffix:' / '+number(m?.context_limit),note:percent==null?'실행기에서 보고한 사용량 / 한도':percent.toFixed(1)+'% 사용',known:m?.context_tokens!=null},
  {label:'생성 속도',value:m?.generation_tps==null?'—':m.generation_tps+' tok/s',note:'최근 측정 구간의 생성 속도',known:m?.generation_tps!=null},
  {label:'입력 토큰',value:number(m?.input_tokens),note:'현재 작업의 누적 입력 토큰',known:m?.input_tokens!=null},
  {label:'출력 토큰',value:number(m?.output_tokens),note:'현재 작업의 누적 출력 토큰',known:m?.output_tokens!=null},
  {label:'모델 요청',value:m?.api_calls==null?'—':number(m.api_calls)+'회',note:'현재 작업의 모델 요청 횟수',known:m?.api_calls!=null},
  {label:'경과 시간',value:m?.elapsed_seconds==null?'—':Math.round(m.elapsed_seconds)+'초',note:'현재 작업의 경과 시간',known:m?.elapsed_seconds!=null},
 ];
 return <dl className="hermes-runtime-metrics" aria-label="모델 실행 정보">
  {facts.map(fact=><div key={fact.label} title={fact.note} className={fact.known?'is-measured':'is-unmeasured'}>
   <dt>{fact.label}</dt><dd>{fact.value}{fact.suffix&&<span>{fact.suffix}</span>}</dd>
  </div>)}
 </dl>;
}
