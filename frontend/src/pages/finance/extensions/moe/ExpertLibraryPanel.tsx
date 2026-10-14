import {PrecisionTolerance,defaultTolerance} from './PrecisionTolerance';
import {useEffect,useState} from 'react';
import type {Champion} from '../../../../data/library';
import {ChampionSpec} from '../../../../ui/ChampionSpec';
import {PackagePlus,Search,WandSparkles,Trash2,Square,SlidersHorizontal,AlertTriangle} from 'lucide-react';
import {useOperations,useSystemState} from '../../../../data/Operations';
import {request} from '../../../../data/api';
import {Button,Drawer,Empty,ErrorMessage,Meter,Tabs} from '../../../../ui/Primitives';
import {bytes,number,inspectionDetail,percent} from '../../../../ui/format';
import {ExpertDiscovery} from './ExpertDiscovery';
import {ExpertVariants} from './ExpertVariants';
import {expertFamilies,expertCategory,categoryNames} from './expertFamilies';

const field='ui-input w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100';
export function ExpertLibraryPanel({initialSource='',sourceSelection=0}:{initialSource?:string;sourceSelection?:number}){
 const {state,refresh,algorithm:algorithmChoice,selectAlgorithm}=useOperations();const lib=state?.library;
 const algorithms=useSystemState<{default:string;items:{name:string}[]}>('algorithms');
 const algorithm=algorithmChoice||algorithms.data?.default||'';
 const [open,setOpen]=useState(false),[source,setSource]=useState(''),[key,setKey]=useState(''),[slot,setSlot]=useState(''),[error,setError]=useState('');
 const [discoveryOpen,setDiscoveryOpen]=useState(false),[manageOpen,setManageOpen]=useState(false),[category,setCategory]=useState('all'),[query,setQuery]=useState('');
 const [tolerance,setTolerance]=useState(defaultTolerance),[device,setDevice]=useState('auto'),[goal,setGoal]=useState('memory'),[precision,setPrecision]=useState('int4');
 const [selectedAction,setSelectedAction]=useState('probe_all'),[actionMessage,setActionMessage]=useState('');
 const [skipChecked,setSkipChecked]=useState(true),[submitting,setSubmitting]=useState(false);
 const [selectedIds,setSelectedIds]=useState<string[]>(()=>{try{const saved=JSON.parse(sessionStorage.getItem('finrl-x.champion.selection')??'null');if(Array.isArray(saved)&&saved.every(id=>typeof id==='string'))return saved}catch{}return state?.experts.active??[]});
 const [selectedFailures,setSelectedFailures]=useState<{source_id:string;precision:string}[]>([]);
 const [creating,setCreating]=useState(false),[championResult,setChampionResult]=useState<Champion|null>(()=>{try{const result=JSON.parse(sessionStorage.getItem('finrl-x.champion.result')??'null');return result?.policy_spaces&&typeof result?.identity?.algorithm==='string'?result:null}catch{return null}});
 useEffect(()=>{sessionStorage.setItem('finrl-x.champion.selection',JSON.stringify(selectedIds))},[selectedIds]);
 useEffect(()=>{if(championResult)sessionStorage.setItem('finrl-x.champion.result',JSON.stringify(championResult))},[championResult]);
 const catalog=lib?.catalog,job=lib?.job,busy=Boolean(job?.busy)||creating||submitting,items=state?.experts.items??[];
 const registeredIds=new Set(items.map(item=>item.id));
 const currentSelection=selectedIds.filter(id=>registeredIds.has(id));
 const chosenExperts=currentSelection.filter(id=>items.some(item=>item.id===id&&item.package_available&&!item.metadata_error&&item.input?.supported));
 useEffect(()=>{if(state)setSelectedIds(current=>current.filter(id=>registeredIds.has(id)))},[state?.experts.items]);
 const families=expertFamilies(items),shown=families.filter(f=>(category==='all'||expertCategory(f.base)===category)&&[f.base.name,f.id,...f.variants.map(v=>v.id)].some(value=>value?.toLowerCase().includes(query.trim().toLowerCase())));
 const candidate=job?.result?.experts?.find((e:any)=>e.id===key);
 const operation=async(kind:string,payload:unknown)=>{
  setError('');setSubmitting(true);try{await request(`library/${kind}`,kind==='probe_all'?{...(payload as Record<string,unknown>),skip_checked:skipChecked}:payload);await refresh();return true}catch(e){setError(e instanceof Error?e.message:'Expert 작업 실패');return false}finally{setSubmitting(false)}
 };
 useEffect(()=>{if(initialSource){setSource(initialSource);setOpen(true);void operation('inspect',{source:initialSource})}},[initialSource,sourceSelection]);
 const toggleManaged=(id:string)=>setSelectedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id]);
 const toggleFailure=(source_id:string,precision:string)=>setSelectedFailures(current=>current.some(row=>row.source_id===source_id&&row.precision===precision)?current.filter(row=>row.source_id!==source_id||row.precision!==precision):[...current,{source_id,precision}]);
 const createChampion=async()=>{setError('');setCreating(true);try{setChampionResult(await request<Champion>('champions/create',{algorithm,experts:[...chosenExperts],...(sessionStorage.getItem('training_currency')?{currency:sessionStorage.getItem('training_currency')}:{} )}));await refresh()}catch(e){setError(e instanceof Error?e.message:'MoE Champion 생성 실패')}finally{setCreating(false)}};
 const removeExpert=async(ids:string[],failures:{source_id:string;precision:string}[]=[])=>{if(!(ids.length+failures.length))return;if(await operation('remove',{ids,failures})){setSelectedIds(current=>current.filter(id=>!ids.includes(id)));setSelectedFailures(current=>current.filter(row=>!failures.some(removed=>removed.source_id===row.source_id&&removed.precision===row.precision)))}};

 const runSelected=async()=>{setError('');setActionMessage('');if(!currentSelection.length&&selectedAction!=='apply'){setError('목록에 있는 모델 버전을 선택하세요.');return}const quality={device,goal,max_relative_rmse:tolerance.error/100,min_action_agreement:tolerance.agreement/100};
  if(selectedAction==='apply'){setSubmitting(true);try{await request('experts/select',{active:currentSelection});await refresh();setActionMessage('운영 Registry에 선택 구성을 적용했습니다. 학습된 Champion의 Expert 구성은 저장된 구성입니다.')}catch(e){setError(e instanceof Error?e.message:'선택 적용 실패')}finally{setSubmitting(false)}}
  else if(selectedAction==='convert'||selectedAction==='optimize'){if(currentSelection.length!==1){setError('이 작업은 모델 버전 1개를 선택하세요. 여러 Expert 최적화는 일괄 최적화를 사용하세요.');return}const id=currentSelection[0];let slot=id+'_'+precision,index=2;while(catalog?.experts?.[slot])slot=id+'_'+precision+'_v'+index++;await operation(selectedAction,{...quality,id,precision,slot})}
  else await operation(selectedAction,{...quality,...(currentSelection.length?{ids:currentSelection}:{})});
 };

 return <section className="expert-library space-y-4">
  <div className="expert-toolbar"><label className="text-xs text-slate-600">정책 알고리즘<select aria-label="MoE 정책 알고리즘" className={field} value={algorithm} disabled={busy||!algorithms.data} onChange={e=>selectAlgorithm(e.target.value)}>{algorithms.data?.items.map(item=><option key={item.name} value={item.name}>{item.name.toUpperCase()}</option>)}</select></label><Button tone="primary" disabled={busy||!chosenExperts.length||!algorithms.data?.items.some(item=>item.name===algorithm)} busy={creating} onClick={()=>void createChampion()}><WandSparkles size={16}/>모델 만들기 <span className="expert-action-count">{chosenExperts.length}</span></Button><Button disabled={busy} onClick={()=>setDiscoveryOpen(true)}><Search size={16}/>Expert 찾기</Button><Button disabled={busy} onClick={()=>setOpen(true)}><PackagePlus size={16}/>가져오기</Button><Button onClick={()=>setManageOpen(true)}><SlidersHorizontal size={16}/>모델 관리</Button>{job?.busy&&<Button tone="danger" onClick={()=>void operation('stop',{})}><Square size={16}/>작업 중지</Button>}</div>
  {!!currentSelection.length&&<div className="expert-selection-summary" role="status"><span><b>{currentSelection.length}</b>개 선택</span><span>구성 가능 <b>{chosenExperts.length}</b>개</span>{!chosenExperts.length&&<span>사용할 모델 버전을 선택하세요</span>}</div>}

  {actionMessage&&<p className="text-xs text-emerald-700">{actionMessage}</p>}
  {!busy&&['optimize','optimize_all','convert'].includes(job?.kind??'')&&job?.result&&<details className="workspace-disclosure rounded-xl bg-white px-4 py-3 text-xs text-slate-600"><summary>최적화·변환 실행 결과 · {job?.kind}</summary><pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(job.result,null,2)}</pre></details>}
  {championResult&&<details className="workspace-disclosure expert-champion-result"><summary>Champion 생성 결과 · Expert 선택 유지</summary><div className="mt-4"><ChampionSpec model={championResult}/></div></details>}
  {!!(selectedIds.length-currentSelection.length)&&<p role="status" className="text-xs text-amber-800">현재 등록 목록에 없는 이전 선택을 제외했습니다.</p>}
  {!!items.filter(item=>!item.name||!item.role||!item.input).length&&<details className="expert-registration-notice"><summary><AlertTriangle size={14}/>등록 정보 확인 필요</summary><p>이름·역할·입력 설정이 빠진 항목이 있습니다. 입력 설정이 없는 모델은 구성에서 제외합니다.</p></details>}
  <div className="expert-browser-toolbar"><div className="overflow-x-auto"><Tabs value={category} onChange={setCategory} items={[{id:'all',label:`전체 ${families.length}`},...Object.entries(categoryNames).map(([id,label])=>({id,label:`${label} ${families.filter(f=>expertCategory(f.base)===id).length}`}))]}/></div><label className="expert-search"><Search size={16}/><input type="search" aria-label="등록 Expert 이름 검색" placeholder="이름으로 검색" value={query} onChange={event=>setQuery(event.target.value)}/></label></div>
  {busy&&<div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-800" aria-live="polite">
   <p>{creating?algorithm.toUpperCase()+' MoE Champion 생성 중':submitting?'요청 전달 중':job?.detail??'Expert 작업 진행 중'}</p>
   {!!job?.total&&<div className="mt-3"><Meter value={(job.completed??0)/job.total*100}/></div>}
  </div>}
  {!busy&&job?.stage==='complete'&&job.kind==='remove'&&<p className="text-xs text-emerald-700" role="status">선택한 등록 항목·실패 기록을 제거했습니다. 모델 파일은 보존했습니다.</p>}
  {!busy&&['quantize','quantize_all','compare','optimize','optimize_all','convert'].includes(job?.kind??'')&&job?.result&&<details open={Boolean(job?.result?.failed||job?.result?.comparison_failed)} className="workspace-disclosure rounded-xl bg-white px-4 py-3 text-xs text-slate-600"><summary className="cursor-pointer">양자화 결과 · 새로 생성 {job.result.created??0} · 기존 버전 {job.result.existing??0} · 생성 실패 {job.result.failed??0} · 출력 비교 {job.result.compared??0} · 비교 실패 {job.result.comparison_failed??0} · 비교 불가 {job.result.comparison_unavailable??0}</summary><ul className="mt-3 space-y-2">{job.result.items?.map((row:any)=><li key={row.id} className={row.status==='failed'?'text-rose-700':row.comparison_error?'text-amber-800':'text-emerald-700'}>{row.id} · {row.precision?.toUpperCase()} · {row.status==='failed'?'생성 실패':row.status==='existing'?'기존 파일 있음':'생성 완료'}{row.bytes!=null?' · '+bytes(row.bytes):''}{row.seconds!=null?' · '+number(row.seconds,2)+'s':''}{row.detail?' · '+inspectionDetail(row.detail):''}{row.comparison_status==='measured'&&<span className="block">원본 비교 완료 · 상대 RMSE {percent(row.relative_rmse)}{row.action_agreement!=null?' · 판단 일치 '+percent(row.action_agreement):''}{row.direction_agreement!=null?' · 방향 일치 '+percent(row.direction_agreement):''}</span>}{row.comparison_error&&<span className="block">원본 비교 {row.comparison_status==='failed'?'실패':'불가'} · {inspectionDetail(row.comparison_error)}</span>}</li>)}</ul></details>}
  {!busy&&['probe_all','load','unload'].includes(job?.kind??'')&&job?.result&&<details open={Boolean(job?.result?.failed)} className="workspace-disclosure rounded-xl bg-white px-4 py-3 text-xs"><summary>선택 작업 결과 · {job?.kind} · 실패 {job.result.failed??0}</summary><ul className="mt-3 space-y-2">{job.result.items?.map((row:any)=><li key={row.id} className={row.status==='failed'?'text-rose-700':'text-slate-600'}>{row.id} · {row.status==='passed'?'검사 통과':row.status==='loaded'?'로드됨':row.status==='unloaded'?'해제됨':row.status==='skipped'?'검사 불가':'실패'}{row.detail?' · '+inspectionDetail(row.detail):''}{row.seconds!=null?' · '+number(row.seconds,2)+'s':''}{row.metrics?.device?' · '+row.metrics.device:''}</li>)}</ul></details>}
  {(error||algorithms.error||job?.error)&&<ErrorMessage message={error||algorithms.error||job?.error||''}/>}
  {!items.length?<Empty title="Expert 등록 항목이 없습니다." detail="Registry가 비어 있습니다. 기존 패키지를 가져오거나 금융 Expert를 검색할 수 있습니다."/>:!shown.length?<Empty title="검색 결과가 없습니다." detail="이름이나 분류를 바꿔서 다시 찾아보세요." action={<Button onClick={()=>{setQuery('');setCategory('all')}}>필터 해제</Button>}/>:<div className="space-y-2">
   {shown.map((family,index)=>{const kind=expertCategory(family.base),selectedVersions=family.variants.filter(item=>selectedIds.includes(item.id)).map(item=>item.id),failures=selectedFailures.filter(row=>row.source_id===family.id);return <div key={family.id}>
    {(index===0||expertCategory(shown[index-1].base)!==kind)&&<h3 className="mb-3 mt-6 text-sm font-semibold text-slate-700">{categoryNames[kind]}</h3>}
    <div className="expert-family-card">
     <div className="expert-family-identity min-w-0"><span className="expert-family-category">{categoryNames[kind]}</span><b>{family.base.name||family.base.id}</b><p>{family.variants.length}개 버전{selectedVersions.length>0&&<span className="expert-family-selected"> · {selectedVersions.length}개 선택</span>}</p></div>
     <ExpertVariants variants={family.variants} quantization={catalog?.quantizations?.[family.id]} legacyFailures={catalog?.optimizations?.[family.id]} selectedIds={selectedIds} selectedFailurePrecisions={selectedFailures.filter(row=>row.source_id===family.id).map(row=>row.precision)} onToggleFailure={precision=>toggleFailure(family.id,precision)} onToggle={toggleManaged}/>
     <details className="expert-family-management text-xs text-slate-500"><summary className="cursor-pointer text-right">버전 관리</summary><div className="flex flex-wrap gap-2"><Button disabled={busy||!family.base.package_available||!family.base.input?.supported||!!family.base.metadata_error||family.base.executor==='repository_source'} onClick={()=>void operation('quantize',{id:family.base.id,device,precision})}><WandSparkles size={14}/>양자화</Button><Button tone="danger" disabled={busy||!(selectedVersions.length+failures.length)} onClick={()=>void removeExpert(selectedVersions,failures)}><Trash2 size={14}/>선택 버전 삭제</Button></div></details>
    </div>
   </div>})}
  </div>}
  <Drawer title="모델 관리" open={manageOpen} onClose={()=>setManageOpen(false)}><ErrorMessage message={error||job?.error||''}/>{busy&&<p className="expert-management-progress" role="status">{submitting?'요청 전달 중':job?.detail??'작업 진행 중'}</p>}<div className="expert-management">   <div className="mt-4 space-y-4"><div className="flex flex-wrap items-center gap-2"><Button disabled={busy||!items.length} onClick={()=>void operation('probe_all',{skip_checked:skipChecked})}>전체 Expert 실행 검사</Button><Button disabled={busy||!items.length} busy={Boolean(job?.busy)&&job?.kind==='quantize_all'} onClick={()=>void operation('quantize_all',{device,precision})}><WandSparkles size={16}/>전체 양자화</Button><label className="flex items-center gap-2 text-xs text-slate-500"><input type="checkbox" checked={skipChecked} onChange={e=>setSkipChecked(e.target.checked)}/>완료된 검사 제외</label></div>
  {!!(items.length+selectedIds.length+selectedFailures.length)&&<div className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-100 px-3 py-2"><span className="mr-1 text-xs font-semibold text-slate-600">{currentSelection.length}개 모델 · 실패 기록 {selectedFailures.length}개 선택</span><select aria-label="선택 Expert 실행 작업" className="ui-input rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs" value={selectedAction} onChange={e=>setSelectedAction(e.target.value)}><option value="apply">운영 구성 적용</option><option value="probe_all">선택 버전 검사</option><option value="load">메모리 로드</option><option value="unload">메모리 해제</option><option value="compare">선택 버전 원본 비교</option><option value="convert">정밀도 변환</option><option value="optimize">개별 최적화</option><option value="optimize_all">전체 / 선택 Expert 최적화</option></select><Button disabled={busy||(!['apply','optimize_all'].includes(selectedAction)&&!currentSelection.length)} onClick={()=>void runSelected()}>선택 작업 실행</Button><Button className="px-3 py-2 text-xs" disabled={busy} onClick={()=>{setSelectedIds([]);setSelectedFailures([])}}>선택 해제</Button><span className="text-[11px] text-slate-500">Registry·실패 기록에서 제거하며 모델 파일은 보존합니다.</span></div>}
  <div className="flex flex-wrap gap-3 text-xs text-slate-500"><label>실행 장치<select aria-label="Expert 실행 장치" className={field} value={device} onChange={e=>setDevice(e.target.value)}><option value="auto">CUDA 우선 · RAM 오프로딩</option><option value="cuda:0">CUDA</option><option value="cpu">CPU</option></select></label><label>최적화 목표<select aria-label="최적화 목표" className={field} value={goal} onChange={e=>setGoal(e.target.value)}><option value="memory">메모리</option><option value="speed">추론 속도</option><option value="balanced">균형</option></select></label><label>변환 정밀도<select aria-label="변환 정밀도" className={field} value={precision} onChange={e=>setPrecision(e.target.value)}>{['fp16','bf16','int8','int4','nf4'].map(v=><option key={v} value={v}>{v.toUpperCase()}</option>)}</select></label><PrecisionTolerance value={tolerance} onChange={setTolerance} disabled={busy}/></div>
   </div></div></Drawer>
  {discoveryOpen&&<ExpertDiscovery onClose={()=>setDiscoveryOpen(false)}/>}
  <Drawer title="Frozen Expert 가져오기" open={open} onClose={()=>setOpen(false)}>
   <div className="space-y-4">
    <ErrorMessage message={error}/>
    <p className="text-sm leading-6 text-slate-500">Expert 패키지 또는 호환 MoE 파일의 로컬 경로·다운로드 주소를 입력하세요. 입력 생성기가 없는 모델은 구성에 넣기 전에 거릅니다.</p>
    <label className="block space-y-2 text-sm"><span>파일 경로 / 다운로드 주소</span><input className={field} value={source} onChange={e=>setSource(e.target.value)} placeholder="C:\모델\expert.pt 또는 https://…"/></label>
    <Button busy={busy&&job?.kind==='inspect'} disabled={busy||!source} onClick={()=>void operation('inspect',{source})}>파일 구성 확인</Button>
    {job?.kind==='inspect'&&!!job?.result?.experts?.length&&<>
     <label className="block space-y-2 text-sm"><span>추가할 Expert / 검증된 입력 템플릿</span><select className={field} value={key} onChange={e=>{setKey(e.target.value);let next=e.target.value,index=2;while(catalog?.experts?.[next])next=e.target.value+'_v'+index++;setSlot(next)}}>
      <option value="">Expert 선택</option>{job.result.experts.map((e:any)=><option key={e.id} value={e.id}>{e.name}{e.input?.supported?'':' · 입력 생성기 없음'}</option>)}
     </select></label>
     {candidate&&<p className={`rounded-xl px-3 py-3 text-sm ${candidate.input?.supported?'bg-emerald-50 text-emerald-700':'bg-amber-50 text-amber-800'}`}>{candidate.input?.requires?.join(' · ')??candidate.input?.reason}</p>}
     {candidate?.native_template&&<p className="text-xs leading-5 text-slate-500">원본 가중치는 선택한 모델의 구조·입력 규칙·학습 종목 범위를 사용합니다. 이 규칙이 달라진 모델은 원본 정의를 포함한 Expert 패키지가 필요합니다.</p>}
     {!!candidate?.input?.universe?.length&&<details className="text-xs text-slate-500"><summary className="cursor-pointer">입력 종목 {candidate.input?.universe.length}개 확인</summary><p className="mt-2 leading-5">{candidate.input?.universe.join(' · ')}</p></details>}
     <label className="block space-y-2 text-sm"><span>슬롯 이름</span><input className={field} value={slot} onChange={e=>setSlot(e.target.value)}/></label>
     <Button tone="primary" disabled={busy||!candidate?.input?.supported||!slot} onClick={()=>void operation('import',{source:job?.result?.source??source,expert_id:key,slot,activate:false})}>가져오기 · 등록</Button>
    </>}
    {busy&&<p className="text-sm text-blue-600" aria-live="polite">{submitting?'요청 전달 중':job?.detail}</p>}
    {job?.error&&<ErrorMessage message={job.error}/>}
   </div>
  </Drawer>
 </section>;
}
