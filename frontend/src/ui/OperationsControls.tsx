import {useState} from 'react';
import {useOperations} from '../data/Operations';
import {Button,ErrorMessage} from './Primitives';
export function OperationsControls(){const {state:s,execute,pending}=useOperations();const [error,setError]=useState('');
 return <div><div className="flex flex-wrap gap-2">{(['feed','paper','engine'] as const).map(name=><Button key={name} busy={pending.has('controls/'+name)} disabled={!s?.operations} tone={s?.operations?.controls[name]?'neutral':'primary'} onClick={async()=>{setError('');try{await execute('controls/'+name,{enabled:!s?.operations?.controls[name]})}catch(e){setError(e instanceof Error?e.message:'제어 실패')}}}>{({feed:'시세 수신',paper:'가상체결',engine:'SAC 자동 판단'})[name]} {s?.operations?.controls[name]?'중지':'시작'}</Button>)}</div><div className="mt-2"><ErrorMessage message={error}/></div>{(s?.operations?.feed.error||s?.operations?.feed.policy_error||s?.operations?.broker?.last_error)&&<p className="mt-2 text-xs text-amber-700">{s?.operations?.feed.error||s?.operations?.feed.policy_error||s?.operations?.broker?.last_error}</p>}</div>;
}
