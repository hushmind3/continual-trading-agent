import {useOperations} from '../data/Operations';
import {Button,ErrorMessage} from './Primitives';
import {Panel,KeyValues} from './Panel';
import {date} from './format';
export function JobLog(){const {state}=useOperations();const [copyError,setCopyError]=useState(''),[copied,setCopied]=useState(false);if(!state)return null;const job=state.job;
  const copy=async()=>{setCopyError('');setCopied(false);try{await navigator.clipboard.writeText(job.log_text);setCopied(true)}catch(e){setCopyError('로그 복사 실패: '+(e instanceof Error?e.message:String(e)))}};
  return <Panel title="공식 실행 로그" description="작업 프로세스의 stdout / stderr · 마지막 최대 32KB" actions={<div className="flex flex-wrap gap-2"><Button disabled={!job.log_text} onClick={()=>void copy()}>로그 복사</Button></div>}>
    <ErrorMessage message={copyError}/>{copied&&<p role="status" className="mb-3 text-xs text-emerald-700">로그를 복사했습니다.</p>}
    <KeyValues items={[['작업',job.command||'대기'],['상태',job.status||'실행 기록 없음'],['PID',job.pid??'없음'],['시작 시각',date(job.started_at)],['종료 시각',date(job.finished_at)],['종료 코드',job.exit_code??'미기록']]}/>
    {job.detail&&<p className="my-3 text-xs text-amber-700">{job.detail}</p>}
    <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-300" tabIndex={0}>{job.log_text||'실행 로그가 없습니다.'}</pre>
  </Panel>;
}
import {useState} from 'react';
