import {Button,Empty,Status} from '@platform/ui/Primitives';
import {MarkdownContent} from '@platform/ui/MarkdownContent';
import {statusNames,type Venture} from './types';
export function BusinessPane({ventures,active,busy,onDecision,compact=false}:{ventures:Venture[];active?:{name:string}|null;busy:boolean;onDecision:(id:string,approve:boolean)=>Promise<unknown>;compact?:boolean}){
 const current=ventures.find(v=>v.status==='pending')||ventures[0];
 return <section aria-label="사업안과 승인" className="space-y-4 p-4 sm:p-5"><header className="flex items-center justify-between gap-2"><h2 className="text-sm font-semibold">사업안과 승인</h2>{current&&<Status tone={current.status==='pending'?'warn':'idle'}>{statusNames[current.status]||current.status}</Status>}</header>
 {!current?<Empty title="아직 제안된 사업안이 없습니다" detail="수익 목표와 고객 문제를 대화로 논의하세요. 예제 상품을 선택한 것으로 처리하지 않습니다."/>:<article className="space-y-4"><h3 className="break-words font-semibold">{current.name}</h3>{(['problem','product','market','validation','execution'] as const).filter((_,index)=>!compact||index<2).map(key=><div key={key}><h4 className="mb-1 text-xs font-medium text-slate-500">{{problem:'고객 문제',product:'제공할 제품',market:'시장 가설',validation:'검증 계획',execution:'실행 계획'}[key]}</h4><MarkdownContent text={String(current.proposal[key]||'미기록')}/></div>)}<p className="text-sm">가설 가격 {Number(current.proposal.price||0).toLocaleString()}원 <span className="text-xs text-slate-400">· 실제 매출 아님</span></p>
 {current.status==='pending'&&<><p className="rounded-xl bg-amber-50 p-3 text-xs leading-6 text-amber-800">{current.name.toLowerCase()==='dealpage'?'승인하면 기본 제공 DealPage 무료 베타를 공개하고 업무를 등록합니다. 결제·정산은 미연결입니다.':'승인하면 사업 검토·기술 준비 업무를 등록합니다. 새 제품의 제작·출시 완료를 의미하지 않습니다.'}</p><div className="flex gap-2"><Button tone="primary" busy={busy} onClick={()=>{void onDecision(current.id,true).catch(()=>{})}}>사업 승인</Button><Button busy={busy} onClick={()=>{void onDecision(current.id,false).catch(()=>{})}}>보류</Button></div></>}
 </article>}
 {active&&<div className="rounded-xl bg-emerald-50 p-3 text-xs text-emerald-800">실제로 공개된 제품 · {active.name}</div>}
 {!compact&&<details className="border-t border-slate-200 pt-4 text-sm"><summary className="cursor-pointer text-slate-500">기본 제공 예제 · DealPage는 무엇인가요?</summary><p className="mt-3 leading-7 text-slate-600">원본에 포함된 제안서 작성용 무료 베타입니다. 새 사업의 정답이나 사용자가 선택한 상품이 아닙니다. 새 사업 초안은 빈 상태에서 생성하며, 승인되지 않은 상품은 공개하지 않습니다. 현재 임의 제품의 자동 제작·배포와 실결제는 별도 구현이 필요합니다.</p></details>}
 </section>;
}
