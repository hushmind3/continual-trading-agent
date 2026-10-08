import {useState} from 'react';
import {FlaskConical,PackagePlus,Plus,Trash2} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {request} from '../../data/api';
import {Button,Drawer,Empty,ErrorMessage,Meter,Status} from '../../ui/Primitives';
import {bytes,date,number} from '../../ui/format';
import type {LibraryState} from '../../data/library';

const field='w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100';
export function ExpertLibraryPanel({onInspect}:{onInspect:(id:string)=>void}){
 const {state,refresh}=useOperations();const lib:LibraryState|undefined=state?.library;
 const [open,setOpen]=useState(false),[source,setSource]=useState(''),[key,setKey]=useState(''),[slot,setSlot]=useState(''),[error,setError]=useState(''),[deleteId,setDeleteId]=useState('');
 const catalog=lib?.catalog,job=lib?.job,busy=Boolean(job?.busy),items=Object.values(catalog?.experts??{});
 const candidate=job?.result?.experts?.find(e=>e.id===key);
 const operation=async(kind:string,payload:unknown)=>{
  setError('');try{await request(`library/${kind}`,payload);await refresh()}catch(e){setError(e instanceof Error?e.message:'Expert 작업 실패')}
 };
 return <section className="space-y-4">
  <header className="flex flex-wrap items-center justify-between gap-3">
   <div><h3 className="text-sm font-bold">Expert 패키지 · 추가 전 검사</h3><p className="mt-1 text-xs text-slate-500">입력 규격과 실제 추론을 확인한 패키지만 MoE에 적용합니다.</p></div>
   <Button disabled={busy} onClick={()=>setOpen(true)}><PackagePlus size={16}/>패키지 가져오기</Button>
  </header>
  {busy&&<div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800" aria-live="polite">
   <p>{job?.detail??'Expert 작업 진행 중'}</p>
   {!!job?.total&&<div className="mt-3"><Meter value={(job.completed??0)/job.total*100}/></div>}
  </div>}
  {!busy&&job?.stage==='complete'&&job.kind==='apply'&&<p className="text-xs text-emerald-700" role="status">슬롯 선택 · 학습 체크포인트 저장 완료</p>}
  {(error||job?.error)&&<ErrorMessage message={error||job?.error||''}/>}
  {!items.length?<Empty title="슬롯 관리 준비" detail="고정 가중치를 독립 패키지로 한 번만 나누고 학습 상태를 이어받습니다." action={<Button busy={busy} onClick={()=>void operation('prepare',{})}>슬롯 관리 준비</Button>}/>:<div className="space-y-2">
   {items.map(item=>{const included=catalog?.active?.includes(item.id),passed=item.check.status==='passed';return <div key={item.id} role="button" tabIndex={0} aria-label={`${item.name} 상세`} onClick={()=>onInspect(item.id)} onKeyDown={e=>{if(e.target===e.currentTarget&&(e.key==='Enter'||e.key===' ')){e.preventDefault();onInspect(item.id)}}} className="flex cursor-pointer flex-wrap items-center justify-between gap-3 rounded-xl bg-white px-4 py-3 transition hover:bg-blue-50/60 focus-visible:outline-2 focus-visible:outline-blue-500">
    <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><b className="text-sm">{item.name}</b><span className="text-xs text-slate-400">{item.id}</span><Status tone={passed?'good':'warn'}>{included?'사용 중':passed?'검사 통과 · 보관':'검사 필요'}</Status></div>
     <p className="mt-1 text-xs text-slate-500">{item.input.requires?.join(' · ')??item.input.reason} · 출력 {item.feature_size-3}D · {item.representation??'원본 정밀도'} · {bytes(item.package.bytes)}</p>
     <p className="mt-1 text-xs text-slate-400">{item.check.detail}{item.check.tested?` · ${date(item.check.tested)}`:''}{item.check.seconds!=null?` · ${number(item.check.seconds,2)}s`:''}</p>
    </div>
    <div className="flex items-center gap-2" onClick={e=>e.stopPropagation()}>
     <Button disabled={busy||!item.input.supported} onClick={()=>void operation('probe',{id:item.id})}><FlaskConical size={14}/>검사</Button>
     {!included&&<Button tone="primary" disabled={busy||!passed} onClick={()=>void operation('apply',{active:[...catalog?.active??[],item.id]})}><Plus size={14}/>사용</Button>}
     {included&&<Button disabled={busy} onClick={()=>void operation('apply',{active:catalog?.active?.filter(k=>k!==item.id)})}>제외</Button>}
     <Button disabled={busy} aria-label={`${item.name} 패키지 삭제`} onClick={()=>setDeleteId(item.id)}><Trash2 size={14}/></Button>
    </div>
   </div>})}
  </div>}
  <Drawer title="Frozen Expert 가져오기" open={open} onClose={()=>setOpen(false)}>
   <div className="space-y-4">
    <p className="text-sm leading-6 text-slate-500">Expert 패키지 또는 호환 MoE 파일의 로컬 경로·다운로드 주소를 입력하세요. 입력 생성기가 없는 모델은 구성에 넣기 전에 거릅니다.</p>
    <label className="block space-y-2 text-sm"><span>파일 경로 / 다운로드 주소</span><input className={field} value={source} onChange={e=>setSource(e.target.value)} placeholder="C:\모델\expert.pt 또는 https://…"/></label>
    <Button busy={busy&&job?.kind==='inspect'} disabled={busy||!source} onClick={()=>void operation('inspect',{source})}>파일 구성 확인</Button>
    {!!job?.result?.experts?.length&&<>
     <label className="block space-y-2 text-sm"><span>추가할 Expert / 검증된 입력 템플릿</span><select className={field} value={key} onChange={e=>{setKey(e.target.value);let next=e.target.value,index=2;while(catalog?.experts?.[next])next=e.target.value+'_v'+index++;setSlot(next)}}>
      <option value="">Expert 선택</option>{job.result.experts.map(e=><option key={e.id} value={e.id}>{e.name}{e.input.supported?'':' · 입력 생성기 없음'}</option>)}
     </select></label>
     {candidate&&<p className={`rounded-xl px-3 py-3 text-sm ${candidate.input.supported?'bg-emerald-50 text-emerald-700':'bg-amber-50 text-amber-800'}`}>{candidate.input.requires?.join(' · ')??candidate.input.reason}</p>}
     {candidate?.native_template&&<p className="text-xs leading-5 text-slate-500">원본 가중치는 선택한 모델의 구조·입력 규칙·학습 종목 범위를 사용합니다. 이 규칙이 달라진 모델은 원본 정의를 포함한 Expert 패키지가 필요합니다.</p>}
     {!!candidate?.input.universe?.length&&<details className="text-xs text-slate-500"><summary className="cursor-pointer">입력 종목 {candidate.input.universe.length}개 확인</summary><p className="mt-2 leading-5">{candidate.input.universe.join(' · ')}</p></details>}
     <label className="block space-y-2 text-sm"><span>슬롯 이름</span><input className={field} value={slot} onChange={e=>setSlot(e.target.value)}/></label>
     <Button tone="primary" disabled={busy||!candidate?.input.supported||!slot} onClick={()=>void operation('import',{source:job?.result?.source??source,expert_id:key,slot})}>가져오기 · 실제 추론 검사</Button>
    </>}
    {busy&&<p className="text-sm text-blue-600" aria-live="polite">{job?.detail}</p>}
    {job?.error&&<ErrorMessage message={job.error}/>}
   </div>
  </Drawer>
  <Drawer title="패키지 삭제" open={Boolean(deleteId)} onClose={()=>setDeleteId('')}>
   <p className="mb-5 text-sm leading-6 text-slate-600">고정 가중치 파일과 이 Expert의 학습 연결을 삭제하고 저장된 정책 버전들도 자동으로 맞춥니다. 다시 사용할 계획이면 제외 버튼으로 연결 상태를 보존하세요.</p>
   <Button tone="danger" disabled={busy} onClick={()=>{void operation('delete',{id:deleteId});setDeleteId('')}}>패키지와 슬롯 삭제</Button>
  </Drawer>
 </section>;
}
