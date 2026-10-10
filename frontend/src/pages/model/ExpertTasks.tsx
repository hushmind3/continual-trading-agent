import {useCallback,useState} from 'react';
import type {Expert} from '../../data/types';
import {useOperations} from '../../data/Operations';
import {Button,Drawer,ErrorMessage,inputClass} from '../../ui/Primitives';
export function ExpertTasks({item}:{item:Expert}) {
 const {state:s,execute,pending}=useOperations();const [open,setOpen]=useState(false),[precision,setPrecision]=useState('fp16'),[slot,setSlot]=useState(''),[error,setError]=useState('');
 const close=useCallback(()=>setOpen(false),[]);
 const job=s?.library?.job;const busy=!!job?.busy||!!s?.job.running;
 const task=async(kind:string,payload:Record<string,unknown>={})=>{setError('');try{await execute('library/'+kind,{id:item.id,...payload});if(kind==='convert')setOpen(false)}catch(e){setError(e instanceof Error?e.message:'모델 작업 실패')}};
 const loaded=s?.operations?.pool.find(p=>p.id===item.id)?.loaded;
 return <div className="space-y-2"><div className="flex flex-wrap gap-2"><Button disabled={busy||!item.package_available} onClick={()=>void task(loaded?'unload':'load')}>{loaded?'메모리 해제':'모델 로드'}</Button><Button disabled={busy||!item.package_available} onClick={()=>void task('probe')}>실제 입력 추론</Button><Button disabled={busy||item.executor==='llama_cpp'||!!item.conversion} onClick={()=>{setSlot(item.id+'_fp16');setOpen(true)}}>정밀도 변환</Button><Button disabled={busy||item.executor==='llama_cpp'||!!item.conversion} onClick={()=>void task('optimize',{goal:'memory'})}>기존 양자화 최적화</Button></div><ErrorMessage message={error}/>
 <Drawer title={item.name+' 정밀도 변환'} open={open} onClose={close}><p className="mb-4 text-xs leading-6 text-slate-500">원본 패키지는 변경하지 않고 기존 변환 모듈로 별도 후보를 저장합니다.</p><label className="block text-xs">정밀도<select className={inputClass+' mt-2'} value={precision} onChange={e=>{setPrecision(e.target.value);setSlot(item.id+'_'+e.target.value)}}>{['fp16','bf16','int8','int4','nf4'].map(v=><option key={v} value={v}>{v.toUpperCase()}</option>)}</select></label><label className="my-4 block text-xs">새 슬롯<input className={inputClass+' mt-2'} value={slot} onChange={e=>setSlot(e.target.value)}/></label><ErrorMessage message={error}/><Button tone="primary" disabled={!slot||busy} busy={pending.has('library/convert')} onClick={()=>void task('convert',{precision,slot,device:'auto'})}>변환 시작</Button></Drawer>
 </div>;
}
