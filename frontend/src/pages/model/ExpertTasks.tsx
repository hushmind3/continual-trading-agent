import {useState} from 'react';
import type {Expert} from '../../data/types';
import {useOperations} from '../../data/Operations';
import {Button,ErrorMessage} from '../../ui/Primitives';
import {ExpertConversion} from './ExpertConversion';

export function ExpertTasks({item}:{item:Expert}){
 const {state:s,execute,pending}=useOperations();
 const [conversion,setConversion]=useState<'convert'|'optimize'|null>(null),[error,setError]=useState('');
 const job=s?.library?.job,busy=!!job?.busy||!!s?.job.running;
 const task=async(kind:'load'|'unload'|'probe')=>{setError('');try{await execute('library/'+kind,{id:item.id})}catch(e){setError(e instanceof Error?e.message:'모델 작업 실패')}};
 const loaded=s?.operations?.pool.find(p=>p.id===item.id)?.loaded;
 const canConvert=item.package_available&&item.input.supported&&item.executor!=='llama_cpp'&&!item.conversion;
 return <div className="space-y-2"><div className="flex flex-wrap gap-2">
  <Button disabled={busy||!item.package_available} busy={pending.has('library/'+(loaded?'unload':'load'))} onClick={()=>void task(loaded?'unload':'load')}>{loaded?'메모리 해제':'모델 로드'}</Button>
  <Button disabled={busy||!item.package_available} busy={pending.has('library/probe')} onClick={()=>void task('probe')}>실제 입력 추론</Button>
  <Button disabled={busy||!canConvert} onClick={()=>setConversion('convert')}>정밀도 변환</Button>
  <Button disabled={busy||!canConvert} onClick={()=>setConversion('optimize')}>기존 양자화 최적화</Button>
 </div><ErrorMessage message={error}/>
 {conversion&&<ExpertConversion key={item.id+conversion} item={item} initialMode={conversion} onClose={()=>setConversion(null)}/>}
 </div>;
}
