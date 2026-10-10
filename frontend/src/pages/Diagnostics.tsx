import {useOperations} from '../data/Operations';
import {useEndpoint} from '../data/useEndpoint';
import {Panel,KeyValues} from '../ui/Panel';
import {Button,ErrorMessage,Skeleton} from '../ui/Primitives';
import {DataTable} from '../ui/DataTable';
import {JobLog} from '../ui/JobLog';
import {bytes,number} from '../ui/format';
interface ModuleInfo {path:string;description:string;functions:string[]}
export function Diagnostics(){const {state:s}=useOperations();const modules=useEndpoint<{items:ModuleInfo[]}>('modules'),logs=useEndpoint<{items:{name:string;text:string}[]}>('logs');if(!s)return <Skeleton/>;
 return <div className="space-y-6"><Panel title="현재 실행 프로세스" description="기존 ResourceMonitor의 실제 PID·RAM·CPU·I/O"><DataTable label="프로세스 자원" items={s.resources.processes} keyFor={r=>String(r.pid)} columns={[{key:'role',label:'대상',render:r=>r.role},{key:'pid',label:'PID',render:r=>r.pid},{key:'ram',label:'RAM',render:r=>bytes(r.rss_bytes)},{key:'cpu',label:'CPU 코어 합산',render:r=>number(r.cpu_percent)+'%'},{key:'threads',label:'스레드',render:r=>r.threads},{key:'io',label:'I/O 누적',render:r=>bytes(r.read_bytes)+' 읽기 / '+bytes(r.write_bytes)+' 쓰기'}]}/></Panel>
 <JobLog/><div className="grid items-start gap-6 lg:grid-cols-2"><Panel title="설치된 라이브러리" description="현재 Python 배포판의 실제 버전"><KeyValues items={Object.entries(s.settings.versions).map(([name,v])=>[name,v])}/><details className="mt-4"><summary className="cursor-pointer text-xs text-blue-600">실제 API 상태 JSON</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-slate-950 p-4 text-xs text-slate-300">{JSON.stringify(s,null,2)}</pre></details></Panel>
 <Panel title="백엔드 로그" description="실제 런타임 파일 · 과거 Streamlit 로그는 파일명으로 구분" actions={<Button busy={logs.loading} onClick={()=>void logs.refresh()}>로그 갱신</Button>}><ErrorMessage message={logs.error}/>{logs.data?.items.map(log=><details key={log.name} className="border-b border-slate-100 py-3"><summary className="cursor-pointer text-sm text-slate-500">{log.name}</summary><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-xl bg-slate-950 p-3 text-xs leading-5 text-slate-300">{log.text}</pre></details>)}</Panel></div>
 <Panel title="백엔드 모듈·함수" description="현재 main의 stockrl 및 공식 FinRL-X 소스 조회"><ErrorMessage message={modules.error}/>{modules.data?.items.map(m=><details key={m.path} className="border-b border-slate-100 py-3"><summary className="cursor-pointer break-words text-xs font-medium text-blue-700">{m.path}</summary><p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-400">{m.description}</p><div className="mt-3 flex flex-wrap gap-2">{m.functions.map(f=><code key={f} className="rounded bg-slate-50 px-2 py-1 text-[11px] text-slate-500">{f}</code>)}</div></details>)}</Panel>
 </div>;
}
