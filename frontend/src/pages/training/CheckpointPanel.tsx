import {useOperations} from '../../data/Operations';
import {Panel} from '../../ui/Panel';
import {Empty,Status} from '../../ui/Primitives';
import {bytes,date,number} from '../../ui/format';
import {Capability} from '../../ui/Capability';
import {useState} from 'react';
import {Button,ErrorMessage} from '../../ui/Primitives';
export function CheckpointPanel(){const {state:s,execute,pending}=useOperations();const [error,setError]=useState(''),[message,setMessage]=useState('');if(!s)return null;
 return <Panel title="저장 정책 · 체크포인트" description="현재 SAC와 보관된 실제 파일 · 원본 경로는 종료 시 저장">
 {s.checkpoints.length?s.checkpoints.map(c=><div key={c.path} className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 py-4"><div><b className="text-sm">{c.name}</b><p className="mt-1 text-xs text-slate-400">{date(c.file.modified)} · {bytes(c.file.bytes)} · {number(c.num_timesteps,0)}단계 / {number(c.updates,0)} 업데이트</p><Status tone={c.compatible?'good':'warn'}>{c.compatible?'현재 설정 식별정보와 호환':'이전 환경 / 정보 부족'}</Status></div><div className="flex gap-3"><a className="text-xs font-semibold text-blue-600" href={'/api/checkpoint?path='+encodeURIComponent(c.path)} download>정책 다운로드</a><Button disabled={!c.compatible||s.job.running} busy={pending.has('checkpoints/restore')} onClick={async()=>{setError('');try{const r=await execute<{message:string}>('checkpoints/restore',{path:c.path});setMessage(r.message)}catch(e){setError(e instanceof Error?e.message:'복원 실패')}}>버전 복원·선택</Button></div></div>):<Empty title="저장된 정책 파일이 없습니다."/>}
 <ErrorMessage message={error}/>{message&&<p className="mt-3 text-xs text-emerald-700">{message}</p>}
 <div className="mt-4"><Capability name="checkpoint_restore" label="과거 정책 버전 복원"/></div>
 </Panel>;
}
