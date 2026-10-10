import {useEffect,useState} from 'react';
import {FlaskConical,PackagePlus,Plus,Gauge,Search,WandSparkles,Play,Power} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {request} from '../../data/api';
import {Button,Drawer,Empty,ErrorMessage,Meter,Status,Tabs} from '../../ui/Primitives';
import {bytes,date,number,inspectionDetail} from '../../ui/format';
import type {LibraryState} from '../../data/library';
import {ExpertConversion} from './ExpertConversion';
import {ExpertDiscovery} from './ExpertDiscovery';
import {ExpertVariants} from './ExpertVariants';
import {expertFamilies,expertCategory,categoryNames} from './expertFamilies';

const field='w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100';
export function ExpertLibraryPanel({onInspect}:{onInspect:(id:string)=>void}){
 const {state,refresh}=useOperations();const [liveLibrary,setLiveLibrary]=useState<LibraryState>();
 useEffect(()=>{let closed=false,timer:ReturnType<typeof setTimeout>;const poll=async()=>{try{const next=await request<LibraryState>('library');if(!closed)setLiveLibrary(next)}catch{}if(!closed)timer=setTimeout(()=>void poll(),2000)};void poll();return()=>{closed=true;clearTimeout(timer)}},[]);
 const lib=liveLibrary??state?.library;
 const [open,setOpen]=useState(false),[source,setSource]=useState(''),[key,setKey]=useState(''),[slot,setSlot]=useState(''),[error,setError]=useState('');
 const [conversionId,setConversionId]=useState('');
 const [discoveryOpen,setDiscoveryOpen]=useState(false),[category,setCategory]=useState('all');
 const [selectedVersions,setSelectedVersions]=useState<Record<string,string>>({});
 const catalog=lib?.catalog,job=lib?.job,busy=Boolean(job?.busy),items=state?.experts.items??[];
 const families=expertFamilies(items),shown=families.filter(f=>category==='all'||expertCategory(f.base)===category);
 const candidate=job?.result?.experts?.find((e:any)=>e.id===key);
 const inspection=job?.kind==='probe_all'&&job.stage==='complete'?{finished:job.finished,reports:(job.result?.items??[]).map((r:any)=>({id:r.id,status:r.status==='passed'?'passed':'failed',detail:r.detail}))}:undefined;
 const inspectionStatus=(item:typeof items[number])=>{
  const result=job?.kind==='probe_all'&&job.stage==='complete'?job.result?.items?.find((r:any)=>r.id===item.id):undefined;
  return result?.status==='passed'?'passed':result?.status==='failed'?'failed':item.check?.status??(item.inference?.status==='ready'?'passed':item.inference?.reason?'failed':undefined);
 };
 const inspectionDetailFor=(item:typeof items[number])=>{
  const result=job?.kind==='probe_all'&&job.stage==='complete'?job.result?.items?.find((r:any)=>r.id===item.id):undefined;
  return result?.detail??item.check?.detail??item.inference?.reason??(item.inference?.status==='ready'?'저장된 실제 추론 결과 통과':'검사 기록 없음');
 };
 const operation=async(kind:string,payload:unknown)=>{
  setError('');try{await request(`library/${kind}`,payload);await refresh()}catch(e){setError(e instanceof Error?e.message:'Expert 작업 실패')}
 };
 return <section className="space-y-4">
  <header className="flex flex-wrap items-center justify-between gap-3">
   <div><h3 className="text-sm font-bold">Expert · 정밀도 버전</h3><p className="mt-1 text-xs text-slate-500">동일 Expert의 원본·FP16·BF16·INT8·INT4·NF4를 한 카드에 표시합니다. 전체 최적화는 등록된 원본 Expert별 후보를 생성하고 실제 출력 품질을 비교합니다.</p></div>
   <div className="flex flex-wrap gap-2"><Button disabled={busy||!families.some(f=>f.base.input.supported&&!f.base.conversion&&f.base.executor!=='llama_cpp')} busy={busy&&job?.kind==='optimize_all'} onClick={()=>void operation('optimize_all',{device:'auto'})}><WandSparkles size={16}/>전체 Expert 버전 생성·최적화</Button><Button disabled={busy||!items.length} busy={busy&&job?.kind==='probe_all'} onClick={()=>void operation('probe_all',{device:'auto'})}><FlaskConical size={16}/>등록 모델 실행 검사</Button><Button disabled={busy} onClick={()=>setDiscoveryOpen(true)}><Search size={16}/>금융 Expert 찾기</Button><Button disabled={busy} onClick={()=>setOpen(true)}><PackagePlus size={16}/>패키지 가져오기</Button></div>
  </header>
  <div className="rounded-xl bg-blue-50 px-4 py-3 text-xs leading-6 text-blue-800">상태·검사·자원 정보는 현재 Registry와 Expert 실행 API 응답을 표시합니다. 검사 기록이 없는 모델은 미확인으로 구분합니다.</div>
  <div className="overflow-x-auto"><Tabs value={category} onChange={setCategory} items={[{id:'all',label:`전체 ${families.length}`},...Object.entries(categoryNames).map(([id,label])=>({id,label:`${label} ${families.filter(f=>expertCategory(f.base)===id).length}`}))]}/></div>
  {busy&&<div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800" aria-live="polite">
   <p>{job?.detail??'Expert 작업 진행 중'}</p>
   {!!job?.total&&<div className="mt-3"><Meter value={(job.completed??0)/job.total*100}/></div>}
  </div>}
  {!busy&&job?.stage==='complete'&&job.kind==='apply'&&<p className="text-xs text-emerald-700" role="status">Expert 구성이 Registry에 저장됐습니다.</p>}
  {!busy&&['probe_all','optimize_all'].includes(job?.kind??'')&&job?.result&&<details open className="rounded-xl bg-white px-4 py-3 text-xs text-slate-600"><summary role="status" className="cursor-pointer">{job.kind==='probe_all'?'전체 Expert 검사':'전체 Expert 버전 생성·최적화'} · 전체 {job.result.total} · 통과 {job.result.passed} · 실패 {job.result.failed} · 건너뜀 {job.result.skipped}</summary><ul className="mt-3 space-y-2">{job.result.items?.map((r:any)=><li key={r.id} className={r.status==='passed'?'text-emerald-700':r.status==='failed'?'text-rose-700':'text-amber-700'}>{r.id} · {r.status==='passed'?'완료':r.status==='failed'?'실패':'건너뜀'}{r.detail?`: ${inspectionDetail(r.detail)}`:''}</li>)}</ul></details>}
  {(error||job?.error)&&<ErrorMessage message={error||job?.error||''}/>}
  {!items.length?<Empty title="Expert 등록 항목이 없습니다." detail="Registry가 비어 있습니다. 기존 패키지를 가져오거나 금융 Expert를 검색할 수 있습니다."/>:<div className="space-y-2">
   {shown.map((family,index)=>{const activeVersion=family.variants.find(v=>catalog?.active?.includes(v.id));const item=family.variants.find(v=>v.id===selectedVersions[family.id])??activeVersion??family.base;const included=catalog?.active?.includes(item.id),check=item.check,checkStatus=inspectionStatus(item),passed=checkStatus==='passed',resources=item.loaded?item.current_resources:item.resources,ram=resources?.ram_bytes??resources?.resident_bytes??resources?.peak_ram_increment,vram=resources?.vram_bytes??resources?.resident_vram_bytes??resources?.peak_vram_bytes,usable=Boolean(item.input.supported&&item.package_available&&(!checkStatus||checkStatus==='passed')&&(!item.conversion||item.conversion.validation?.passed!==false)),kind=expertCategory(family.base);return <div key={family.id}>{(index===0||expertCategory(shown[index-1].base)!==kind)&&<h3 className="mb-3 mt-6 flex items-center gap-2 text-sm font-semibold text-slate-700">{categoryNames[kind]}<span className="text-xs font-normal text-slate-400">{families.filter(f=>expertCategory(f.base)===kind).length}개 Expert</span></h3>}<div role="button" tabIndex={0} aria-label={`${family.base.name} 상세`} onClick={()=>onInspect(item.id)} onKeyDown={e=>{if(e.target===e.currentTarget&&(e.key==='Enter'||e.key===' ')){e.preventDefault();onInspect(item.id)}}} className="grid cursor-pointer gap-4 rounded-xl bg-white px-4 py-4 transition hover:bg-blue-50/60 focus-visible:outline-2 focus-visible:outline-blue-500 xl:grid-cols-[minmax(220px,.8fr)_minmax(0,1.6fr)_auto] xl:items-center">
    <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><b className="text-sm">{family.base.name}</b><Status tone={passed?'good':'warn'}>{included?'현재 SAC 관측 구성':passed?'검사 통과 · 미사용':checkStatus==='failed'?'검사 실패':item.package_available?'검사 상태 미확인':'패키지 파일 없음'}</Status></div>
     <p className="mt-1 text-xs text-slate-500">{item.input.requires?.join(' · ')??item.input.reason} · 출력 {item.feature_size-3}D · {item.representation??'원본 정밀도'} · {bytes(item.weight_bytes??item.package.bytes)}</p>
     <p className="mt-1 text-xs text-slate-500">{item.input.universe?.length?`원본 학습 ${item.input.universe.length}종목 전용`:'입력 종목 범위 제한 정보 없음'}{check?.metrics?.device?` · 검사 ${String(check.metrics.device)}`:''}</p>
     <p className="mt-1 break-words text-xs text-slate-400">{inspectionDetail(inspectionDetailFor(item))}{check?.tested?` · ${date(check.tested)}`:item.inference?.as_of?` · ${date(item.inference.as_of)}`:''}{check?.seconds!=null?` · ${number(check.seconds,2)}s`:''}</p>
     <p className="mt-2 text-xs font-semibold text-blue-700">{item.loaded?'적재 중':'미적재'}{resources?.device?` · ${String(resources.device)}`:''} · RAM {bytes(typeof ram==='number'?ram:undefined)} · VRAM {bytes(typeof vram==='number'?vram:undefined)}</p>
     {catalog?.optimizations?.[family.id]&&<p className="mt-2 text-xs text-blue-700">{catalog.optimizations[family.id].stage==='complete'?`최적 후보: ${catalog.optimizations[family.id].selected??'미지정'}`:catalog.optimizations[family.id].error??catalog.optimizations[family.id].stage}</p>}
    </div>
    <ExpertVariants base={family.base} optimization={catalog?.optimizations?.[family.id]} variants={family.variants} selected={item.id} active={catalog?.active??[]} inspection={inspection} onSelect={id=>setSelectedVersions({...selectedVersions,[family.id]:id})}/>
    <div className="flex flex-wrap items-center gap-2" onClick={e=>e.stopPropagation()}>
     <Button disabled={busy||!family.base.input.supported||Boolean(family.base.conversion)||family.base.executor==='llama_cpp'} onClick={()=>void operation('optimize',{id:family.id,goal:'memory',device:'auto'})}><WandSparkles size={14}/>이 Expert 자동 양자화</Button>
     <Button disabled={busy||!family.base.input.supported||Boolean(family.base.conversion)||family.base.executor==='llama_cpp'} aria-label={`${family.base.name} 정밀도 변환`} onClick={()=>setConversionId(family.base.id)}><Gauge size={14}/>변환</Button>
     <Button disabled={busy||!item.package_available} onClick={()=>void operation(item.loaded?'unload':'load',{id:item.id})}><Power size={14}/>{item.loaded?'해제':'적재'}</Button>
     <Button disabled={busy||!item.package_available||!item.input.supported} busy={busy&&job?.kind==='probe'&&job?.result?.id===item.id} onClick={()=>void operation('probe',{id:item.id})}><Play size={14}/>추론 실행</Button>
     {!included&&<Button tone="primary" disabled={busy||!usable} onClick={()=>void operation('apply',{active:[...(catalog?.active??[]).filter(k=>!family.variants.some(v=>v.id===k)),item.id]})}><Plus size={14}/>{activeVersion?'이 버전으로 교체':'사용'}</Button>}
     {included&&<Button disabled={busy} onClick={()=>void operation('apply',{active:catalog?.active?.filter(k=>k!==item.id)})}>제외</Button>}
     
    </div>
   </div></div>})}
  </div>}
  {conversionId&&state?.experts.items.find(e=>e.id===conversionId)&&<ExpertConversion key={conversionId} item={state.experts.items.find(e=>e.id===conversionId)!} onClose={()=>setConversionId('')}/>}
  {discoveryOpen&&<ExpertDiscovery onClose={()=>setDiscoveryOpen(false)}/>}
  <Drawer title="Frozen Expert 가져오기" open={open} onClose={()=>setOpen(false)}>
   <div className="space-y-4">
    <p className="text-sm leading-6 text-slate-500">Expert 패키지 또는 호환 MoE 파일의 로컬 경로·다운로드 주소를 입력하세요. 입력 생성기가 없는 모델은 구성에 넣기 전에 거릅니다.</p>
    <label className="block space-y-2 text-sm"><span>파일 경로 / 다운로드 주소</span><input className={field} value={source} onChange={e=>setSource(e.target.value)} placeholder="C:\모델\expert.pt 또는 https://…"/></label>
    <Button busy={busy&&job?.kind==='inspect'} disabled={busy||!source} onClick={()=>void operation('inspect',{source})}>파일 구성 확인</Button>
    {job?.kind==='inspect'&&!!job?.result?.experts?.length&&<>
     <label className="block space-y-2 text-sm"><span>추가할 Expert / 검증된 입력 템플릿</span><select className={field} value={key} onChange={e=>{setKey(e.target.value);let next=e.target.value,index=2;while(catalog?.experts?.[next])next=e.target.value+'_v'+index++;setSlot(next)}}>
      <option value="">Expert 선택</option>{job.result.experts.map((e:any)=><option key={e.id} value={e.id}>{e.name}{e.input.supported?'':' · 입력 생성기 없음'}</option>)}
     </select></label>
     {candidate&&<p className={`rounded-xl px-3 py-3 text-sm ${candidate.input.supported?'bg-emerald-50 text-emerald-700':'bg-amber-50 text-amber-800'}`}>{candidate.input.requires?.join(' · ')??candidate.input.reason}</p>}
     {candidate?.native_template&&<p className="text-xs leading-5 text-slate-500">원본 가중치는 선택한 모델의 구조·입력 규칙·학습 종목 범위를 사용합니다. 이 규칙이 달라진 모델은 원본 정의를 포함한 Expert 패키지가 필요합니다.</p>}
     {!!candidate?.input.universe?.length&&<details className="text-xs text-slate-500"><summary className="cursor-pointer">입력 종목 {candidate.input.universe.length}개 확인</summary><p className="mt-2 leading-5">{candidate.input.universe.join(' · ')}</p></details>}
     <label className="block space-y-2 text-sm"><span>슬롯 이름</span><input className={field} value={slot} onChange={e=>setSlot(e.target.value)}/></label>
     <Button tone="primary" disabled={busy||!candidate?.input.supported||!slot} onClick={()=>void operation('import',{source:job?.result?.source??source,expert_id:key,slot,activate:true})}>가져오기 · 자동 등록</Button>
    </>}
    {busy&&<p className="text-sm text-blue-600" aria-live="polite">{job?.detail}</p>}
    {job?.error&&<ErrorMessage message={job.error}/>}
   </div>
  </Drawer>
 </section>;
}
