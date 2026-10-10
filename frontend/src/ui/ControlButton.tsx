import {useState} from 'react';
import {Square} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {Button,ErrorMessage} from './Primitives';
export function StopButton(){const {state,execute,pending}=useOperations();const [error,setError]=useState('');
  return <div className="space-y-2"><Button tone="danger" disabled={!state?.job.running} busy={pending.has('stop')} onClick={async()=>{setError('');try{await execute('stop',{})}catch(e){setError(e instanceof Error?e.message:'정지 실패')}}}><Square size={14}/>작업 중지</Button><ErrorMessage message={error}/></div>;
}
