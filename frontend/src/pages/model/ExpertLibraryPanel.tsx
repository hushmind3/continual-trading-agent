import {useState} from 'react';
import {FlaskConical,PackagePlus,Plus,Trash2,Gauge,Search,WandSparkles} from 'lucide-react';
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
 const {state,refresh}=useOperations();const lib:LibraryState|undefined=state?.library;
 const [open,setOpen]=useState(false),[source,setSource]=useState(''),[key,setKey]=useState(''),[slot,setSlot]=useState(''),[error,setError]=useState(''),[deleteId,setDeleteId]=useState('');
 const [conversionId,setConversionId]=useState('');
 const [discoveryOpen,setDiscoveryOpen]=useState(false),[category,setCategory]=useState('all');
 const [selectedVersions,setSelectedVersions]=useState<Record<string,string>>({});
 const catalog=lib?.catalog,job=lib?.job,busy=Boolean(job?.busy),items=Object.values(catalog?.experts??{});
 const families=expertFamilies(items),shown=families.filter(f=>category==='all'||expertCategory(f.base)===category);
 const candidate=job?.result?.experts?.find(e=>e.id===key);
 const operation=async(kind:string,payload:unknown)=>{
  setError('');try{await request(`library/${kind}`,payload);await refresh()}catch(e){setError(e instanceof Error?e.message:'Expert 작업 실패')}
 };
 return <section className="space-y-4">
  <header className="flex flex-wrap items-center justify-between gap-3">
   <div><h3 className="text-sm font-bold">Expert · 정밀도 버전</h3><p className="mt-1 text-xs text-slate-500">전체 검사는 보관된 파일을 검사합니다. 자동 최적화는 정밀도별 변환·측정·선택 이유를 보여줍니다.</p></div>
   <div className="flex flex-wrap gap-2"><Button disabled={busy||!items.length} onClick={()=>void operation('optimize_all',{device:'auto',validation_mode:'functional'})}><WandSparkles size={16}/>사용 중 Expert 자동 양자화</Button><Button disabled={busy||!items.length} busy={busy&&job?.kind==='probe_all'} onClick={()=>void operation('probe_all',{device:'auto'})}><FlaskConical size={16}/>등록 모델 실행 검사</Button><Button disabled={busy} onClick={()=>setDiscoveryOpen(true)}><Search size={16}/>금융 Expert 찾기</Button><Button disabled={busy} onClick={()=>setOpen(true)}><PackagePlus size={16}/>패키지 가져오기</Button></div>
  </header>
  <div className="rounded-xl bg-blue-50 px-4 py-3 text-xs leading-6 text-blue-800">GPU 상주 우선 · VRAM 초과분만 RAM 유지 · 출력 검증 후 메모리 절감으로 선택 · CPU/GPU 속도 배수는 선택 기준에서 제외</div>
  <div className="overflow-x-auto"><Tabs value={category} onChange={setCategory} items={[{id:'all',label:`전체 ${families.length}`},...Object.entries(categoryNames).map(([id,label])=>({id,label:`${label} ${families.filter(f=>expertCategory(f.base)===id).length}`}))]}/></div>
  {catalog?.admission&&<p className="text-xs text-blue-700" role="status">{catalog.admission.stage==='blocked'?'자동 추가 차단':'최근 자동 추가'} · {catalog.experts?.[catalog.admission.id]?.name??catalog.admission.id} · {date(catalog.admission.time)} · {catalog.admission.stage==='blocked'?catalog.admission.detail:catalog.active?.includes(catalog.admission.id)?'현재 운영 구성에 포함':'현재는 제외됨'}</p>}
  {busy&&<div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800" aria-live="polite">
   <p>{job?.detail??'Expert 작업 진행 중'}</p>
   {!!job?.total&&<div className="mt-3"><Meter value={(job.completed??0)/job.total*100}/></div>}
  </div>}
  {!busy&&job?.stage==='complete'&&job.kind==='apply'&&<p className="text-xs text-emerald-700" role="status">슬롯 선택 · 학습 체크포인트 저장 완료</p>}
  {catalog?.inspection?.finished&&<details className="rounded-xl bg-white px-4 py-3 text-xs text-slate-600"><summary className="cursor-pointer" role="status">전체 검사 {catalog.inspection.completed}/{catalog.inspection.total} · 통과 {catalog.inspection.passed??0} · 출력 기준 초과 {catalog.inspection.quality_warning??0} · 실패 {catalog.inspection.failed??0} · {date(catalog.inspection.finished)}</summary><p className="mt-2">원본·변환 버전 모두 자동 검사 · CUDA/RAM 여유에 따라 장치 선택 · 같은 원본의 버전은 동일 입력 비교</p><ul className="mt-3 space-y-2">{catalog.inspection.reports.map(r=><li key={r.id} className={r.status==='passed'?'text-emerald-700':'text-amber-700'}>{r.name} · {r.status==='passed'?'통과':r.status==='quality_warning'?'출력 기준 초과':'실패'}: {inspectionDetail(r.detail)}</li>)}</ul></details>}
  {(error||job?.error)&&<ErrorMessage message={error||job?.error||''}/>}
  {!items.length?<Empty title="슬롯 관리 준비" detail="고정 가중치를 독립 패키지로 한 번만 나누고 학습 상태를 이어받습니다." action={<Button busy={busy} onClick={()=>void operation('prepare',{})}>슬롯 관리 준비</Button>}/>:<div className="space-y-2">
   {shown.map((family,index)=>{const activeVersion=family.variants.find(v=>catalog?.active?.includes(v.id));const item=family.variants.find(v=>v.id===selectedVersions[family.id])??activeVersion??family.base;const included=catalog?.active?.includes(item.id),usable=(item.quantized||['nf4','int4','int8'].includes(item.conversion?.precision??'')||item.executor==='llama_cpp')&&item.check.status==='passed'&&(!item.conversion||item.conversion.validation?.passed===true),passed=item.check.status==='passed',kind=expertCategory(family.base);return <div key={family.id}>{(index===0||expertCategory(shown[index-1].base)!==kind)&&<h3 className="mb-3 mt-6 flex items-center gap-2 text-sm font-semibold text-slate-700">{categoryNames[kind]}<span className="text-xs font-normal text-slate-400">{families.filter(f=>expertCategory(f.base)===kind).length}개 Expert · 파일 버전 수와 구분</span></h3>}<div role="button" tabIndex={0} aria-label={`${family.base.name} 상세`} onClick={()=>onInspect(item.id)} onKeyDown={e=>{if(e.target===e.currentTarget&&(e.key==='Enter'||e.key===' ')){e.preventDefault();onInspect(item.id)}}} className="grid cursor-pointer gap-4 rounded-xl bg-white px-4 py-4 transition hover:bg-blue-50/60 focus-visible:outline-2 focus-visible:outline-blue-500 xl:grid-cols-[minmax(220px,.8fr)_minmax(0,1.6fr)_auto] xl:items-center">
    <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><b className="text-sm">{family.base.name}</b><Status tone={passed?'good':'warn'}>{included?'운영 구성에 포함':usable?'실행 검사 통과 · 미사용':passed?'원본 참조 · 미사용':item.check.status==='quality_warning'?'출력 차이 큼 · 교체 차단':'검사 필요'}</Status></div>
     <p className="mt-1 text-xs text-slate-500">{item.input.requires?.join(' · ')??item.input.reason} · 출력 {item.feature_size-3}D · {item.representation??'원본 정밀도'} · {bytes(item.weight_bytes??item.package.bytes)}</p>
     <p className="mt-1 text-xs text-slate-500">{item.input.universe?.length?`원본 학습 ${item.input.universe.length}종목 전용`:'시계열이 확보된 관찰 종목에 공통 적용'}{item.check.metrics?.device?` · 검사 ${item.check.metrics.device}`:''}</p>
     <p className="mt-1 break-words text-xs text-slate-400">{inspectionDetail(item.check.detail)}{item.check.tested?` · ${date(item.check.tested)}`:''}{item.check.seconds!=null?` · ${number(item.check.seconds,2)}s`:''}</p>
     {state?.experts.find(e=>e.id===item.id)?.residency&&<p className="mt-2 text-xs font-semibold text-blue-700">{({gpu_resident:'GPU · VRAM 상주',ram_offload:'VRAM 초과분 · RAM 유지',gpu_ram_layer_offload:'GPU 추론 · 초과 레이어 RAM 오프로드',gpu_cpu_hybrid:'GPU/CPU 혼합 추론',temporary:'일시 실행',unloaded:'미적재'} as Record<string,string>)[state.experts.find(e=>e.id===item.id)!.residency!]??'적재 확인 중'} · VRAM {bytes(state.experts.find(e=>e.id===item.id)?.resident_bytes)}</p>}
     {catalog?.optimizations?.[family.id]&&<p className="mt-2 text-xs text-blue-700">{catalog.optimizations[family.id].replacement_required?catalog.optimizations[family.id].detail:catalog.optimizations[family.id].stage==='complete'?`자동 판단 · ${catalog.optimizations[family.id].applied?'교체 완료':'현재 버전 유지 / 최적 후보 보관'}`:catalog.optimizations[family.id].stage==='error'?catalog.optimizations[family.id].error:'같은 실제 입력으로 정밀도 버전을 비교하는 중'}</p>}
    </div>
    <ExpertVariants base={family.base} optimization={catalog?.optimizations?.[family.id]} inspection={catalog?.inspection} variants={family.variants} selected={item.id} active={catalog?.active??[]} onSelect={id=>setSelectedVersions({...selectedVersions,[family.id]:id})}/>
    <div className="flex flex-wrap items-center gap-2" onClick={e=>e.stopPropagation()}>
     <Button disabled={busy||!family.base.input.supported||Boolean(family.base.conversion)||family.base.executor==='llama_cpp'} onClick={()=>void operation('optimize',{id:family.id,goal:'memory',device:'auto'})}><WandSparkles size={14}/>이 Expert 자동 양자화</Button>
     <Button disabled={busy||!family.base.input.supported||Boolean(family.base.conversion)||family.base.executor==='llama_cpp'} aria-label={`${family.base.name} 정밀도 변환`} onClick={()=>setConversionId(family.base.id)}><Gauge size={14}/>변환</Button>
     {!included&&<Button tone="primary" disabled={busy||!usable} onClick={()=>void operation('apply',{active:[...(catalog?.active??[]).filter(k=>!family.variants.some(v=>v.id===k)),item.id]})}><Plus size={14}/>{activeVersion?'이 버전으로 교체':'사용'}</Button>}
     {included&&<Button disabled={busy} onClick={()=>void operation('apply',{active:catalog?.active?.filter(k=>k!==item.id)})}>제외</Button>}
     <Button disabled={busy} aria-label={`${item.name} 패키지 삭제`} onClick={()=>setDeleteId(item.id)}><Trash2 size={14}/></Button>
    </div>
   </div></div>})}
  </div>}
  {conversionId&&catalog?.experts?.[conversionId]&&<ExpertConversion key={conversionId} item={catalog.experts[conversionId]} onClose={()=>setConversionId('')}/>}
  {discoveryOpen&&<ExpertDiscovery onClose={()=>setDiscoveryOpen(false)}/>}
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
     <Button tone="primary" disabled={busy||!candidate?.input.supported||!slot} onClick={()=>void operation('import',{source:job?.result?.source??source,expert_id:key,slot})}>가져오기 · 검사 · 자동 사용</Button>
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
