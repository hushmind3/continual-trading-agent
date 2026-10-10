import {useOperations} from '../data/Operations';
import {Button} from './Primitives';
import {Panel,KeyValues} from './Panel';
import {StopButton} from './ControlButton';
import {date} from './format';
export function JobLog(){const {state}=useOperations();if(!state)return null;const job=state.job;
  return <Panel title="공식 실행 로그" description="작업 프로세스의 stdout / stderr · 마지막 최대 32KB" actions={<div className="flex flex-wrap gap-2"><Button disabled={!job.log_text} onClick={()=>void navigator.clipboard.writeText(job.log_text)}>로그 복사</Button><StopButton/></div>}>
    <KeyValues items={[['작업',job.command||'대기'],['상태',job.status||'실행 기록 없음'],['PID',job.pid??'없음'],['시작 시각',date(job.started_at)],['종료 시각',date(job.finished_at)],['종료 코드',job.exit_code??'미기록']]}/>
    {job.detail&&<p className="my-3 text-xs text-amber-700">{job.detail}</p>}
    {job.running&&<p className="my-3 text-xs text-slate-500">SAC·Replay는 정상 종료 시 저장됩니다. 중지하면 이번 실행 중 새 경험은 저장되지 않습니다.</p>}
    <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-300" tabIndex={0}>{job.log_text||'실행 로그가 없습니다.'}</pre>
  </Panel>;
}
