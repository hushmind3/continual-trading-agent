import {useState} from 'react';
import {Button,ErrorMessage,inputClass} from '../../ui/Primitives';
import {useOperations} from '../../data/Operations';
import {Panel} from '../../ui/Panel';
import {DataTable,type Column} from '../../ui/DataTable';
import type {Expert} from '../../data/types';
import {bytes} from '../../ui/format';
import {Capability} from '../../ui/Capability';
const columns:Column<Expert>[]=[{key:'name',label:'Expert',render:e=>e.name},{key:'precision',label:'정밀도',render:e=>e.representation},
 {key:'package',label:'패키지',render:e=>bytes(e.package.bytes),sort:e=>e.package.bytes},{key:'device',label:'마지막 장치',render:e=>String(e.resources.device||'미측정')},
 {key:'ram',label:'마지막 RAM',render:e=>bytes((e.resources.peak_ram_bytes??e.resources.peak_ram_increment) as number|undefined)},
 {key:'vram',label:'마지막 VRAM',render:e=>bytes((e.resources.peak_vram_bytes??e.resources.resident_bytes) as number|undefined)}];
export function ExpertComparison(){const {state:s,execute,pending}=useOperations();const [baseline,setBaseline]=useState(''),[variant,setVariant]=useState(''),[error,setError]=useState('');if(!s)return null;return <Panel title="Expert 비교 · 기록된 자원" description="기록된 자원 조회 · 사용자가 요청한 동일 실제 입력 추론 비교"><div className="mb-5 flex flex-wrap items-end gap-3">{[['baseline',baseline,setBaseline],['variant',variant,setVariant]].map(([label,value,set])=><label key={String(label)} className="text-xs">{label==='baseline'?'원본 기준':'비교 버전'}<select className={inputClass+' mt-2'} value={value as string} onChange={e=>(set as (id:string)=>void)(e.target.value)}><option value="">선택</option>{s.experts.items.filter(e=>e.package_available).map(e=><option key={e.id} value={e.id}>{e.name}</option>)}</select></label>)}<Button disabled={!baseline||!variant||s.library?.job.busy||s.job.running} busy={pending.has('library/compare')} onClick={async()=>{setError('');try{await execute('library/compare',{baseline,variant});}catch(e){setError(e instanceof Error?e.message:String(e));}}}>실제 입력 비교 실행</Button></div><ErrorMessage message={error}/><DataTable label="Expert 자원 비교" items={s.experts.items} columns={columns} keyFor={e=>e.id} searchText={e=>e.name+' '+e.id}/><div className="mt-5 grid gap-3 sm:grid-cols-2"><Capability name="conversion" label="자동 양자화·정밀도 검사"/><Capability name="discovery" label="금융 Expert 검색·자동 등록"/></div></Panel>}
