import {Download,ExternalLink} from 'lucide-react';
import type {DiscoveredExpert} from '../../data/library';
import {Button,Status} from '../../ui/Primitives';
import {bytes,calendarDate,number} from '../../ui/format';

export function ExpertSearchResult({item,busy,onDownload}:{item:DiscoveredExpert;busy:boolean;onDownload:()=>void}){
 const installed=Boolean(item.installed_versions?.length);
 return <article className="space-y-3 rounded-xl border border-slate-100 bg-white p-4">
  <div className="flex items-start justify-between gap-3"><a href={item.url} target="_blank" rel="noreferrer" className="flex min-w-0 items-center gap-2 break-all text-sm font-semibold text-blue-800">{item.repository}<ExternalLink size={13} className="shrink-0"/></a><Status tone={item.same_weights?'neutral':item.compatible?'good':'warn'}>{item.same_weights?'동일 가중치 보유':installed?'다른 버전 보유':item.compatible?'검사 가능':'입력·실행기 확인 필요'}</Status></div>
  <p className="text-xs text-slate-400">{item.source??'Hugging Face'} · {item.domain}{item.source!=='GitHub'?` · 다운로드 ${number(item.downloads,0)}`:''}</p>
  <div className="grid gap-x-4 gap-y-2 text-xs sm:grid-cols-2">
   <p><span className="text-slate-400">가중치 파일 </span>{bytes(item.bytes)}</p>
   <p><span className="text-slate-400">릴리즈 </span>{item.release_date?<a href={item.release_source} target="_blank" rel="noreferrer">{calendarDate(item.release_date)}</a>:'원본에 날짜 미기재'}</p>
   <p><span className="text-slate-400">저장소 등록 </span>{calendarDate(item.created)}</p>
   <p><span className="text-slate-400">최근 업데이트 </span>{calendarDate(item.updated)}</p>
  </div>
  <div className="space-y-2 rounded-xl bg-slate-50 px-3 py-3 text-xs leading-5">
   <p><b>필요 입력</b> · {item.input_summary??'원본 입력 규격 확인 필요'}</p>
   <p><b>API</b> · {item.api_requirement??'미확인'}</p>
   <p><b>역할 중복</b> · {item.overlap?.length?`${item.overlap.length}개 보유 모델과 같은 입력 역할`:'현재 검증한 입력 역할과 겹침 미확인'}</p>
   {!!item.installed_versions?.length&&<p><b>설치됨</b> · {item.installed_versions.map(v=>`${v.name} (${v.revision?.slice(0,8)??'원본 revision 미기록'}${v.active?' · 사용 중':''})`).join(' / ')}</p>}
   <p className="text-slate-500">{item.resource_note}</p>
  </div>
  <p className="text-xs leading-5 text-slate-500">{item.detail}</p>
  <details className="text-xs text-slate-500"><summary className="cursor-pointer">입력 근거 · 중복 역할 · 버전 확인</summary><div className="mt-2 space-y-2 break-words leading-5">
   <p>고정 revision: {item.revision}</p>{item.template_name&&<p>입력 실행기: {item.template_name}</p>}
   {!!item.overlap?.length&&<p>{item.overlap.join(' · ')} · {item.overlap_basis}</p>}
   <p>등록일·수정일을 모델 릴리즈 날짜로 사용하지 않습니다.</p>
   <a className="text-blue-700" href={item.input_evidence?.source??item.url} target="_blank" rel="noreferrer">원본 모델 설명 확인 ↗</a>
   {item.input_evidence?.snippets.map((line,index)=><blockquote key={index} className="border-l-2 border-slate-200 pl-3">{line}</blockquote>)}
   {!item.requirements_verified&&<p className="text-amber-700">문서 단서는 입력 계약의 검증 결과가 아닙니다. 실행기·입력 연결이 확인되기 전에는 추가할 수 없습니다.</p>}
  </div></details>
  <Button disabled={busy||!item.compatible||item.same_weights} tone="primary" onClick={onDownload}><Download size={14}/>다운로드 · 검사 · 자동 사용</Button>
 </article>;
}
