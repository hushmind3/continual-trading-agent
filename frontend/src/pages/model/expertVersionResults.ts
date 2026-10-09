import type {LibraryExpert,Optimization,OptimizationReport,Inspection} from '../../data/library';
import {inspectionDetail,number} from '../../ui/format';

export interface VersionResult {
 key:string;label:string;versions:LibraryExpert[];item?:LibraryExpert;report?:OptimizationReport;
 inspection:{label:string;detail:string;status:string};decision:{label:string;detail:string;status:string};
}
export function precisionOf(item:LibraryExpert){return item.conversion?.precision.toLowerCase()??'original'}

function decision(report:OptimizationReport|undefined,optimization:Optimization|undefined,key:string):VersionResult['decision']{
 const attempt=optimization?.attempts?.[key];
 const failure=optimization?.failures?.find(f=>f.precision.toLowerCase()===key);
 if(attempt?.status==='failed'||failure)return {label:'최적화 실패',detail:inspectionDetail(attempt?.detail??failure!.detail),status:'failed'};
 if(!report)return {label:optimization?.stage==='measuring'?(attempt?.status==='running'?'검사 중':'검사 순서 대기'):'최적화 미실행',detail:attempt?.detail??'이 정밀도의 최적화 결과가 없습니다.',status:'pending'};
 if(optimization?.selected===report.id)return {label:'최적화 선택',detail:report.reason??(optimization.previous===report.id?'5% 이상 개선되는 적격 후보가 없어 현재 버전 유지':'정확도·속도·메모리 기준에서 가장 유리한 후보'),status:'selected'};
 if(!report.passed)return {label:'출력 기준 탈락',detail:inspectionDetail(report.reason??report.detail??'출력 차이 허용 기준을 넘었습니다.'),status:'rejected'};
 if(report.eligible===false)return {label:'성능 기준 탈락',detail:report.reason??`현재 버전보다 추론 시간이 ${optimization?.goal==='memory'?'50':'15'}% 넘게 증가해 제외`,status:'rejected'};
 return {label:'통과 · 미선택',detail:report.reason??(optimization?.selected===optimization?.previous&&(report.score??0)>=1?`현재 기준보다 목표 점수가 ${number(((report.score??1)-1)*100,1)}% 불리함`:optimization?.selected===optimization?.previous&&(report.score??0)>.95?'목표 점수 개선이 5% 미만':'선택된 버전보다 목표 점수가 높음 · 낮을수록 유리'),status:'not_selected'};
}

export function versionResults(base:LibraryExpert,variants:LibraryExpert[],selected:string,active:string[],optimization?:Optimization,inspection?:Inspection):VersionResult[]{
 return (base.executor==='llama_cpp'?['original']:['original','fp16','bf16','int8','int4','nf4']).map(key=>{
  const versions=variants.filter(v=>precisionOf(v)===key);
  const reports=optimization?.reports?.filter(r=>key==='original'?r.id===base.id:r.precision.toLowerCase().startsWith(key))??[];
  const item=versions.find(v=>v.id===selected)??versions.find(v=>active.includes(v.id))??versions.find(v=>v.id===reports.at(-1)?.id)??versions[0];
  const report=reports.find(r=>r.id===item?.id)??reports.at(-1);
  const native=key!=='original'&&!versions.length&&base.representation?.split(' · ')[0].toLowerCase()===key&&!report;
  if(native)return {key,label:key.toUpperCase(),versions:[],inspection:{label:'원본과 같은 정밀도',detail:'원본 패키지가 이미 이 정밀도입니다. 별도 변환 파일이 필요하지 않습니다.',status:'native'},decision:{label:'별도 변환 불필요',detail:`원본 ${base.id}의 검사 결과를 확인하세요.`,status:'native'}};
  const check=item?.check;
  const tested=(check?.tested??0)>(inspection?.finished??Infinity)?undefined:inspection?.reports.find(r=>r.id===item?.id);
  const waiting=inspection&&!inspection.finished&&item&&(check?.tested??0)<(inspection.started??0);
  const status=tested?.status??(waiting?'pending':check?.status);
  const detail=tested?.detail??check?.detail;
  const inspected=(!item?{label:report?'파일 정리됨':'미생성',detail:report?'최적화 판단은 보존 · 현재 패키지 없음':'변환되지 않았거나 변환에 실패해 현재 패키지가 없습니다.',status:'absent'}:
   status==='passed'?{label:tested?'전체 검사 통과':'추론 검사 통과',detail:detail??'실제 입력 추론 통과',status:'passed'}:
   status==='quality_warning'?{label:'출력 기준 초과',detail:detail??'허용 오차 초과',status:'rejected'}:
   status==='failed'?{label:'추론 검사 실패',detail:inspectionDetail(detail??'추론 실패'),status:'failed'}:
   {label:'미검사 / 검사 대기',detail:detail??'아직 실제 검사를 완료하지 않았습니다.',status:'pending'});
  return {key,label:key==='original'?(base.representation?.split(' · ')[0]??'원본'):key.toUpperCase(),versions,item,report,inspection:inspected,decision:decision(report,optimization,key)};
 });
}
