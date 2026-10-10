import {useState} from 'react';
import {Search} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {Button,Drawer,Empty,ErrorMessage} from '../../ui/Primitives';
import {ExpertSearchResult} from './ExpertSearchResult';

export function ExpertDiscovery({onClose}:{onClose:()=>void}){
 const {state,execute}=useOperations();const [query,setQuery]=useState(''),[error,setError]=useState(''),[filter,setFilter]=useState('all'),[days,setDays]=useState(365);
 const library=state?.library,job=library?.job,busy=Boolean(job?.busy),found=library?.catalog.discovery;
 const run=async(kind:'search'|'acquire',payload:Record<string,unknown>)=>{setError('');try{await execute('library/'+kind,payload)}catch(e){setError(e instanceof Error?e.message:'검색·다운로드 실패')}};
 const models=found?.models.filter(m=>filter==='all'||filter==='ready'&&m.compatible&&!m.same_weights||filter==='installed'&&(m.same_weights||m.installed_versions?.length)||filter==='new'&&!m.same_weights&&!m.installed_versions?.length)??[];
 return <Drawer title="금융 Expert 탐색" open onClose={onClose}>
  <div className="space-y-4">
   <p className="text-sm leading-6 text-slate-600">금융 모델과 시장 예측에 활용할 수 있는 시계열 모델을 함께 찾습니다. 설치 중복·입력 연결·파일 크기를 먼저 확인하고, 선택한 후보만 내려받아 실제 검사합니다.</p>
   <label className="flex items-center gap-3 text-xs text-slate-500">최근 모델 범위<select aria-label="모델 공개 검색 기간" value={days} onChange={e=>setDays(Number(e.target.value))} className="rounded-xl bg-white px-3 py-2"><option value={90}>최근 3개월</option><option value={180}>최근 6개월</option><option value={365}>최근 1년</option><option value={3650}>전체 공개 모델</option></select></label>
   <Button tone="primary" busy={busy&&job?.kind==='search'} disabled={busy} onClick={()=>void run('search',{preset:'finance',recent_days:days})}><Search size={16}/>금융 Expert 자동 검색</Button>
   <details className="text-xs text-slate-500"><summary className="cursor-pointer">이름으로 직접 검색</summary><form className="mt-3 flex gap-2" onSubmit={e=>{e.preventDefault();void run('search',{query,recent_days:days})}}><input aria-label="공개 모델 검색어" className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500" value={query} onChange={e=>setQuery(e.target.value)} placeholder="알고 있는 모델 이름"/><Button type="submit" disabled={busy||!query.trim()}>검색</Button></form></details>
   {busy&&<p className="rounded-xl bg-blue-50 px-3 py-3 text-sm text-blue-700" aria-live="polite">{job?.detail}</p>}
   {(error||job?.error)&&<ErrorMessage message={error||job?.error||''}/>}
   {found&&<><p className="text-xs leading-5 text-slate-500">{found.query} · {found.models.filter(m=>m.compatible&&!m.same_weights).length}개 검사 가능한 후보</p>{found.keywords&&<p className="text-xs text-slate-400">검색 범위: {found.keywords.join(' · ')} · Hugging Face + GitHub · 최신 공개/업데이트 순</p>}<select aria-label="검색 결과 필터" value={filter} onChange={e=>setFilter(e.target.value)} className="rounded-xl bg-white px-3 py-2 text-sm"><option value="all">모든 결과</option><option value="ready">현재 검사 가능한 새 가중치</option><option value="new">미설치 모델</option><option value="installed">이미 설치한 모델 / 다른 버전</option></select></>}
   {found?.errors?.map(e=><p key={e.query} className="text-xs text-amber-700">{e.query} 검색 실패 · {e.detail}</p>)}
   {models.map(item=>{
    const registered=state?.experts.items.find(expert=>{
     const origin=typeof expert.origin==='object'&&expert.origin!==null?expert.origin:null;
     return origin?.repository===item.repository&&origin?.revision===item.revision;
    });
    return <ExpertSearchResult key={item.id} item={item} busy={busy} registered={Boolean(registered)} active={Boolean(registered?.active)} onDownload={()=>void run('acquire',{id:item.id,device:'auto'})}/>;
   })}
   {found&&!models.length&&<Empty title="조건에 맞는 후보가 없습니다." detail="필터를 바꾸거나 모델 이름으로 검색하세요."/>}
   {found&&<p className="text-xs leading-5 text-slate-500">{found.scope}</p>}
   {!busy&&job?.kind==='acquire'&&job.stage==='complete'&&<p className="text-sm text-emerald-700">다운로드·등록이 완료되어 현재 Expert 사용 구성에 적용했습니다.</p>}
  </div>
 </Drawer>;
}
