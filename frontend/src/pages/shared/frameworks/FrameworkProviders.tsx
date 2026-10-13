import {useState} from 'react';
import {useSystemState,useOperations} from '../../../data/Operations';
import {Panel} from '../../../ui/Panel';
import {Button,ErrorMessage,inputClass} from '../../../ui/Primitives';
export function FrameworkProviders(){
 const provider=useSystemState<{items:{name:string;fields:string[];configured:boolean;status:string}[]}>('framework/providers'),{execute,pending}=useOperations();
 const [values,setValues]=useState<Record<string,string>>({}),[error,setError]=useState(''),[message,setMessage]=useState('');
 const save=async(name:string,fields:string[])=>{setError('');try{await execute('framework/providers/'+name,Object.fromEntries(fields.filter(key=>values[key]).map(key=>[key,values[key]])));setValues(v=>Object.fromEntries(Object.entries(v).filter(([key])=>!fields.includes(key))));setMessage(name+' 설정을 OS 보안 저장소에 저장했습니다. 인증·수신은 실제 실행 시 확인합니다.');}catch(e){setError(e instanceof Error?e.message:'공식 공급원 설정 실패')}};
 return <Panel title="공식 공급원 연결 설정" description="원형 환경변수 이름으로 저장하고 공식 작업 프로세스에 전달합니다. 값은 OS keyring에 저장하며 소스·JSON·GitHub에 기록하지 않습니다.">
 <ErrorMessage message={error||provider.error}/><p className="mb-3 text-xs text-emerald-700">{message}</p><div className="space-y-5">{provider.data?.items.map(p=><section key={p.name}><p className="mb-3 text-sm font-semibold">{p.name} · {p.configured?'인증 값 설정됨':'설정 필요'}</p><p className="mb-3 text-xs text-slate-500">{p.status}</p><div className="grid gap-3 sm:grid-cols-2">{p.fields.map(key=><label key={key} className="text-xs text-slate-500">{key}<input className={inputClass+' mt-2'} type={key.endsWith('BASE_URL')||key.endsWith('USERNAME')?'text':'password'} autoComplete="off" value={values[key]??''} placeholder="비워두면 기존 값 유지" onChange={e=>setValues(v=>({...v,[key]:e.target.value}))}/></label>)}</div><Button className="mt-3" disabled={!p.fields.some(key=>values[key])} busy={pending.has('framework/providers/'+p.name)} onClick={()=>void save(p.name,p.fields)}>보안 설정 저장</Button></section>)}</div>
 </Panel>;
}
