import {useCallback,useState} from 'react';
import {useOperations} from '../../data/Operations';
import {useEndpoint} from '../../data/useEndpoint';
import type {DiscoveryModel} from '../../data/types';
import {Panel} from '../../ui/Panel';
import {DataTable} from '../../ui/DataTable';
import {Button,Drawer,ErrorMessage,inputClass} from '../../ui/Primitives';
import {bytes} from '../../ui/format';
interface ModelFile {path:string;name:string;format:string;bytes:number;registered?:string}
interface Inspection {source:string;experts:{id:string;name:string;input:{supported:boolean;reason?:string}}[]}
export function ModelFolderPanel(){
 const {state:s,execute,pending}=useOperations();const files=useEndpoint<{root:string;files:ModelFile[]}>('models');
 const [source,setSource]=useState(''),[slot,setSlot]=useState(''),[key,setKey]=useState(''),[query,setQuery]=useState(''),[error,setError]=useState('');
 const close=useCallback(()=>setSource(''),[]);const job=s?.library?.job;
 const result=job?.kind==='inspect'?job.result as Inspection|undefined:undefined;
 const models=s?.library?.catalog.discovery?.models||[];
 const task=async(kind:string,payload:Record<string,unknown>)=>{setError('');try{await execute('library/'+kind,payload)}catch(e){setError(e instanceof Error?e.message:'작업 요청 실패')}};
 return <div className="space-y-6"><Panel title="바탕화면 모델 폴더" description={files.data?.root||'실제 외부 모델 경로 조회 중'} actions={<Button busy={files.loading} onClick={()=>void files.refresh()}>폴더 다시 조회</Button>}><ErrorMessage message={files.error}/>
 {files.data&&<DataTable label="외부 모델 파일" items={files.data.files} keyFor={r=>r.path} searchText={r=>r.name} columns={[{key:'name',label:'실제 파일',render:r=>r.name},{key:'size',label:'크기',render:r=>bytes(r.bytes)},{key:'registered',label:'등록',render:r=>r.registered||'미등록'}, {key:'inspect',label:'조회·등록',render:r=><Button disabled={job?.busy} onClick={()=>{setSource(r.path);setKey('');setSlot('');void task('inspect',{source:r.path})}}>구조·입력 확인</Button>}]}/>}
 <p className="mt-4 text-xs text-slate-400">모델 원본은 이동·수정·삭제·재다운로드하지 않습니다. 기존 패키지는 파일을 참조해 등록합니다.</p>
 </Panel><Panel title="Expert 검색 · 다운로드 · 자동 등록" description="복구한 Hugging Face/GitHub 검색 및 원본 호환 확인 모듈"><div className="flex gap-3"><input className={inputClass} value={query} onChange={e=>setQuery(e.target.value)} placeholder="모델·금융 시계열 키워드"/><Button disabled={job?.busy} busy={pending.has('library/search')} onClick={()=>void task('search',{query})}>공개 Expert 검색</Button></div><ErrorMessage message={error}/>
 <div className="mt-4"><DataTable<DiscoveryModel> label="검색 결과" items={models} keyFor={r=>r.id} searchText={r=>r.repository} columns={[{key:'repo',label:'모델',render:r=>r.repository},{key:'bytes',label:'크기',render:r=>bytes(r.bytes)},{key:'status',label:'입력 계약',render:r=>r.detail||'조회됨'}, {key:'acquire',label:'등록',render:r=><Button disabled={job?.busy||!r.compatible||r.same_weights} onClick={()=>void task('acquire',{id:r.id,activate:true})}>{r.same_weights?'이미 보관':'다운로드·자동 등록'}</Button>}]}/></div>
 </Panel>{job&&<Panel title="현재 모델 작업" description={job.kind}><p className="text-sm">{job.stage} · {job.detail}</p><ErrorMessage message={job.error||''}/>{job.result!=null&&job.kind!=='search'&&<pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-slate-50 p-3 text-xs">{JSON.stringify(job.result,null,2)}</pre>}</Panel>}
 <Drawer title="기존 모델 확인·등록" open={!!source} onClose={close}><p className="mb-4 break-all text-xs text-slate-400">{source}</p><ErrorMessage message={job?.error||error}/>{result?.source===source&&<div className="space-y-4"><label className="block text-xs">원본 계약 / 템플릿<select className={inputClass+' mt-2'} value={key} onChange={e=>setKey(e.target.value)}><option value="">선택</option>{result.experts.map(e=><option key={e.id} value={e.id} disabled={!e.input.supported}>{e.name}{!e.input.supported?' · '+e.input.reason:''}</option>)}</select></label><label className="block text-xs">새 등록 슬롯<input className={inputClass+' mt-2'} value={slot} onChange={e=>setSlot(e.target.value)} placeholder="my_existing_expert"/></label><Button tone="primary" disabled={!slot||!key||job?.busy} onClick={()=>void task('import',{source,slot,expert_id:key,template:key,activate:true})}>원본 참조·등록·선택</Button></div>}</Drawer>
 </div>;
}
