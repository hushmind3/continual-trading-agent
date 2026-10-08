import {useState} from 'react';
import {Download,Search,ExternalLink} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {request} from '../../data/api';
import {Button,Drawer,Empty,ErrorMessage,Status} from '../../ui/Primitives';
import {bytes,date,number} from '../../ui/format';

export function ExpertDiscovery({onClose}:{onClose:()=>void}){
 const {state,refresh}=useOperations();const [query,setQuery]=useState('chronos'),[error,setError]=useState('');
 const library=state?.library,job=library?.job,busy=Boolean(job?.busy),found=library?.catalog.discovery;
 const run=async(kind:string,payload:unknown)=>{setError('');try{await request('library/'+kind,payload);await refresh()}catch(e){setError(e instanceof Error?e.message:'검색·다운로드 실패')}};
 return <Drawer title="공개 Expert 검색 · 다운로드 · 검사" open onClose={onClose}>
  <div className="space-y-4">
   <p className="text-sm leading-6 text-slate-600">공개 저장소의 실제 파일과 입력 구조를 확인합니다. 호환 후보를 선택하면 모델 폴더에 내려받고 원본 추론·자원 검사를 자동 진행합니다.</p>
   <form className="flex gap-2" onSubmit={e=>{e.preventDefault();void run('search',{query})}}><input aria-label="공개 모델 검색어" className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500" value={query} onChange={e=>setQuery(e.target.value)} placeholder="chronos, timesfm, TimeMoE…"/><Button type="submit" busy={busy&&job?.kind==='search'} disabled={busy||!query}><Search size={15}/>검색</Button></form>
   {busy&&<p className="rounded-xl bg-blue-50 px-3 py-3 text-sm text-blue-700" aria-live="polite">{job?.detail}</p>}
   {(error||job?.error)&&<ErrorMessage message={error||job?.error||''}/>}
   {found&&<p className="text-xs leading-5 text-slate-500">{found.query} · {found.models.filter(m=>m.compatible&&!m.same_weights).length}개 검사 가능한 후보 · {found.scope}</p>}
   {found?.models.map(item=><article key={item.id} className="space-y-3 rounded-xl border border-slate-100 bg-white p-4">
    <div className="flex items-start justify-between gap-3"><a href={item.url} target="_blank" rel="noreferrer" className="flex min-w-0 items-center gap-2 break-all text-sm font-semibold text-blue-800">{item.repository}<ExternalLink size={13} className="shrink-0"/></a><Status tone={item.same_weights?'neutral':item.compatible?'good':'warn'}>{item.same_weights?'이미 보유':item.compatible?'검사 후보':'입력 연결 필요'}</Status></div>
    <p className="text-xs leading-5 text-slate-500">{item.detail}</p>
    <p className="text-xs text-slate-400">{item.bytes?bytes(item.bytes)+' · ':''}업데이트 {date(item.updated)} · 다운로드 {number(item.downloads,0)}</p>
    {item.template_name&&<p className="text-xs text-slate-500">입력 템플릿: {item.template_name}</p>}
    <Button disabled={busy||!item.compatible||item.same_weights} tone="primary" onClick={()=>void run('acquire',{id:item.id,device:'auto'})}><Download size={14}/>다운로드 · 검사</Button>
   </article>)}
   {found&&!found.models.length&&<Empty title="공개 검색 결과가 없습니다." detail="모델 이름이나 입력 계열로 다시 검색하세요."/>}
   {!busy&&job?.kind==='acquire'&&job.stage==='complete'&&(job.result?.check?.status==='passed'?<p className="text-sm text-emerald-700">실제 검사 완료 · 라이브러리에서 사용 여부를 선택하세요.</p>:<ErrorMessage message={job.result?.check?.detail??'후보 검사 결과를 확인하세요.'}/>)}
  </div>
 </Drawer>;
}
