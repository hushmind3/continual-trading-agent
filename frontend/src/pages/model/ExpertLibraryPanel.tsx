import {useState} from 'react';
import {PackagePlus,Search,WandSparkles,Trash2,Square} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {request} from '../../data/api';
import {Button,Drawer,Empty,ErrorMessage,Meter,Tabs} from '../../ui/Primitives';
import {bytes,number,inspectionDetail,percent} from '../../ui/format';
import {ExpertDiscovery} from './ExpertDiscovery';
import {ExpertVariants} from './ExpertVariants';
import {expertFamilies,expertCategory,categoryNames} from './expertFamilies';

const field='w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100';
type ChampionResult={name:string;path:string;identity:{currency:string;symbols:string[];champion_experts:string[]}};
export function ExpertLibraryPanel(){
 const {state,refresh}=useOperations();const lib=state?.library;
 const [open,setOpen]=useState(false),[source,setSource]=useState(''),[key,setKey]=useState(''),[slot,setSlot]=useState(''),[error,setError]=useState('');
 const [discoveryOpen,setDiscoveryOpen]=useState(false),[category,setCategory]=useState('all');
 const [selectedIds,setSelectedIds]=useState<string[]>(()=>state?.experts.active??[]);
 const [selectedFailures,setSelectedFailures]=useState<{source_id:string;precision:string}[]>([]);
 const [creating,setCreating]=useState(false),[championResult,setChampionResult]=useState<ChampionResult|null>(null);
 const catalog=lib?.catalog,job=lib?.job,busy=Boolean(job?.busy)||creating,items=state?.experts.items??[];
 const chosenExperts=selectedIds;
 const families=expertFamilies(items),shown=families.filter(f=>category==='all'||expertCategory(f.base)===category);
 const candidate=job?.result?.experts?.find((e:any)=>e.id===key);
 const operation=async(kind:string,payload:unknown)=>{
  setError('');try{await request(`library/${kind}`,payload);await refresh();return true}catch(e){setError(e instanceof Error?e.message:'Expert 작업 실패');return false}
 };
 const toggleManaged=(id:string)=>setSelectedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id]);
 const toggleFailure=(source_id:string,precision:string)=>setSelectedFailures(current=>current.some(row=>row.source_id===source_id&&row.precision===precision)?current.filter(row=>row.source_id!==source_id||row.precision!==precision):[...current,{source_id,precision}]);
 const createChampion=async()=>{setError('');setChampionResult(null);setCreating(true);try{setChampionResult(await request<ChampionResult>('champions/create',{experts:chosenExperts}));await refresh()}catch(e){setError(e instanceof Error?e.message:'SAC Champion 생성 실패')}finally{setCreating(false)}};
 const removeExpert=async(ids:string[],failures:{source_id:string;precision:string}[]=[])=>{if(!(ids.length+failures.length))return;if(await operation('remove',{ids,failures})){setSelectedIds(current=>current.filter(id=>!ids.includes(id)));setSelectedFailures(current=>current.filter(row=>!failures.some(removed=>removed.source_id===row.source_id&&removed.precision===row.precision)))}};
 const removeSelected=()=>removeExpert(selectedIds,selectedFailures);
 return <section className="space-y-4">
  <header className="flex flex-wrap items-center justify-between gap-3">
   <div><h3 className="text-sm font-bold">Expert · 정밀도 버전</h3><p className="mt-1 text-xs text-slate-500">모델 버전을 선택해 SAC Champion을 생성합니다. 양자화 결과는 정밀도·가중치 크기·계층 수·실패 이유로 표시합니다.</p></div>
   <div className="flex flex-wrap gap-2"><Button tone="primary" disabled={busy} busy={creating} onClick={()=>void createChampion()}><WandSparkles size={16}/>SAC Champion 생성 · {chosenExperts.length}개</Button><Button disabled={busy||!items.length} busy={Boolean(job?.busy)&&job?.kind==='quantize_all'} onClick={()=>void operation('quantize_all',{device:'auto'})}><WandSparkles size={16}/>전체 양자화</Button><Button disabled={busy} onClick={()=>setDiscoveryOpen(true)}><Search size={16}/>금융 Expert 찾기</Button><Button disabled={busy} onClick={()=>setOpen(true)}><PackagePlus size={16}/>패키지 가져오기</Button>{job?.busy&&<Button tone="danger" onClick={()=>void operation('stop',{})}><Square size={16}/>작업 중지</Button>}</div>
  </header>
  {!!(selectedIds.length+selectedFailures.length)&&<div className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-100 px-3 py-2"><span className="mr-1 text-xs font-semibold text-slate-600">{selectedIds.length}개 모델 · 실패 기록 {selectedFailures.length}개 선택</span><Button tone="danger" className="px-3 py-2 text-xs" disabled={busy} onClick={()=>void removeSelected()}><Trash2 size={14}/>선택 항목 삭제</Button><Button className="px-3 py-2 text-xs" disabled={busy} onClick={()=>{setSelectedIds([]);setSelectedFailures([])}}>선택 해제</Button><span className="text-[11px] text-slate-500">Registry·실패 기록에서 제거하며 모델 파일은 보존합니다.</span></div>}
  {championResult&&<p role="status" className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{championResult.name} 생성 완료 · 미학습 · {championResult.identity.currency} {championResult.identity.symbols.join(', ')} · Expert {championResult.identity.champion_experts.length}개 · {championResult.path}</p>}
  <div className="overflow-x-auto"><Tabs value={category} onChange={setCategory} items={[{id:'all',label:`전체 ${families.length}`},...Object.entries(categoryNames).map(([id,label])=>({id,label:`${label} ${families.filter(f=>expertCategory(f.base)===id).length}`}))]}/></div>
  {busy&&<div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800" aria-live="polite">
   <p>{creating?'선택 모델로 SAC Champion 생성 중':job?.detail??'Expert 작업 진행 중'}</p>
   {!!job?.total&&<div className="mt-3"><Meter value={(job.completed??0)/job.total*100}/></div>}
  </div>}
  {!busy&&job?.stage==='complete'&&job.kind==='remove'&&<p className="text-xs text-emerald-700" role="status">선택한 등록 항목·실패 기록을 제거했습니다. 모델 파일은 보존했습니다.</p>}
  {!busy&&['quantize','quantize_all'].includes(job?.kind??'')&&job?.result&&<details open className="rounded-xl bg-white px-4 py-3 text-xs text-slate-600"><summary className="cursor-pointer">양자화 결과 · 새로 생성 {job.result.created??0} · 기존 버전 {job.result.existing??0} · 생성 실패 {job.result.failed??0} · 출력 비교 {job.result.compared??0} · 비교 실패 {job.result.comparison_failed??0} · 비교 불가 {job.result.comparison_unavailable??0}</summary><ul className="mt-3 space-y-2">{job.result.items?.map((row:any)=><li key={row.id} className={row.status==='failed'?'text-rose-700':row.comparison_error?'text-amber-800':'text-emerald-700'}>{row.id} · {row.precision?.toUpperCase()} · {row.status==='failed'?'생성 실패':row.status==='existing'?'기존 파일 있음':'생성 완료'}{row.bytes!=null?' · '+bytes(row.bytes):''}{row.seconds!=null?' · '+number(row.seconds,2)+'s':''}{row.detail?' · '+inspectionDetail(row.detail):''}{row.comparison_status==='measured'&&<span className="block">원본 비교 완료 · 상대 RMSE {percent(row.relative_rmse)}{row.action_agreement!=null?' · 판단 일치 '+percent(row.action_agreement):''}{row.direction_agreement!=null?' · 방향 일치 '+percent(row.direction_agreement):''}</span>}{row.comparison_error&&<span className="block">원본 비교 {row.comparison_status==='failed'?'실패':'불가'} · {inspectionDetail(row.comparison_error)}</span>}</li>)}</ul></details>}
  {(error||job?.error)&&<ErrorMessage message={error||job?.error||''}/>}
  {!items.length?<Empty title="Expert 등록 항목이 없습니다." detail="Registry가 비어 있습니다. 기존 패키지를 가져오거나 금융 Expert를 검색할 수 있습니다."/>:<div className="space-y-2">
   {shown.map((family,index)=>{const kind=expertCategory(family.base),selectedVersions=family.variants.filter(item=>selectedIds.includes(item.id)).map(item=>item.id),failures=selectedFailures.filter(row=>row.source_id===family.id);return <div key={family.id}>
    {(index===0||expertCategory(shown[index-1].base)!==kind)&&<h3 className="mb-3 mt-6 text-sm font-semibold text-slate-700">{categoryNames[kind]}</h3>}
    <div className="grid gap-4 rounded-xl bg-white px-4 py-4 xl:grid-cols-[minmax(200px,.7fr)_minmax(0,1.6fr)_auto] xl:items-center">
     <div className="min-w-0"><b className="text-sm">{family.base.name}</b><p className="mt-1 text-xs text-slate-500">Frozen Expert · {number(family.base.parameters,0)} parameters</p>{!!family.base.input.universe?.length&&<p className="mt-1 text-xs text-slate-400">원본 학습 종목 {family.base.input.universe.length}개</p>}</div>
     <ExpertVariants variants={family.variants} quantization={catalog?.quantizations?.[family.id]} legacyFailures={catalog?.optimizations?.[family.id]} selectedIds={selectedIds} selectedFailurePrecisions={selectedFailures.filter(row=>row.source_id===family.id).map(row=>row.precision)} onToggleFailure={precision=>toggleFailure(family.id,precision)} onToggle={toggleManaged}/>
     <div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={()=>void operation('quantize',{id:family.base.id,device:'auto'})}><WandSparkles size={14}/>양자화</Button><Button tone="danger" disabled={busy||!(selectedVersions.length+failures.length)} onClick={()=>void removeExpert(selectedVersions,failures)}><Trash2 size={14}/>선택 버전 삭제</Button></div>
    </div>
   </div>})}
  </div>}
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
