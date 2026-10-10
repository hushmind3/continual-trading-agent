import {Workflow} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {Skeleton} from '../ui/Primitives';
import {Panel,KeyValues} from '../ui/Panel';
import {TrainingReadiness} from '../ui/TrainingReadiness';
import {JobLog} from '../ui/JobLog';
import {bytes,number} from '../ui/format';
import {SacControls} from './training/SacControls';
import {PolicyArchitecture} from './training/PolicyArchitecture';
import {CheckpointPanel} from './training/CheckpointPanel';
import {HelpDisclosure} from '../ui/HelpDisclosure';
export function TrainingWorkspace(){const {state:s}=useOperations();if(!s)return <Skeleton/>;const buffer=s.model.replay_state,m=s.job.measurements;
 return <div className="space-y-6"><section className="rounded-2xl bg-[#edf0fc] p-6"><div className="flex flex-wrap justify-between gap-4"><div><p className="flex items-center gap-2 text-xs text-violet-600"><Workflow size={15}/>FinRL-X · 공식 SAC</p><h2 className="mt-2 text-2xl font-bold">시장 경험으로 정책 가중치 업데이트</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Frozen Expert의 관측을 원본 FinRL 환경에 연결하고 SB3 Actor·Twin Critic·Replay로 학습합니다.</p></div><TrainingReadiness/></div><div className="mt-6 grid gap-5 sm:grid-cols-3">{[['저장된 학습 단계',number(s.model.num_timesteps,0)],['저장된 가중치 업데이트',number(s.model.updates,0)],['이번 실행 로그 단계',m.total_timesteps!=null?number(m.total_timesteps,0):'로그 기록 없음']].map(([k,v])=><div key={k}><p className="text-xs text-slate-500">{k}</p><b className="mt-2 block text-xl">{v}</b></div>)}</div></section>
 <SacControls/>
 <Panel title="Replay Buffer · 학습 지표" description="공식 Replay 저장 파일 / SB3 출력 로그의 실제 값">
 <KeyValues items={[['저장된 Replay 경험',number(buffer.size,0)],['버퍼 용량',number(buffer.capacity,0)],['현재 포인터',number(buffer.position,0)],['Buffer full',buffer.full==null?'미기록':String(buffer.full)],['Replay 파일 크기',bytes(s.model.replay.bytes)],['배열 할당 메모리',bytes(buffer.array_bytes)],['로그 actor_loss',number(m.actor_loss,6)],['로그 critic_loss',number(m.critic_loss,6)],['로그 ent_coef',number(m.ent_coef,6)],['로그 n_updates',number(m.n_updates,0)]]}/>
 {buffer.error&&<p className="text-xs text-amber-700">{buffer.error}</p>}
 <p className="mt-4 text-xs text-slate-400">로그 지표는 마지막 출력 시점, Replay 수치는 마지막 저장 시점 기준입니다. 실행 중 미저장 경험을 저장값으로 표시하지 않습니다.</p>
 </Panel>
 <div className="grid items-start gap-6 lg:grid-cols-2"><PolicyArchitecture/><Panel title="학습 설정" description="공식 예제 적용값과 SB3 라이브러리 기본값 · 읽기 전용"><h3 className="text-sm font-semibold">FinRL-X train_sac 적용값</h3><KeyValues items={Object.entries(s.settings.parameters).map(([k,v])=>[k,String(v)])}/><details className="mt-4"><summary className="cursor-pointer text-xs text-blue-600">SB3 기본값·환경 설정 펼치기</summary><KeyValues items={Object.entries(s.settings.sb3_defaults).map(([k,v])=>[k,JSON.stringify(v)])}/><KeyValues items={Object.entries(s.settings.environment_args).map(([k,v])=>[k,String(v)])}/></details><HelpDisclosure title="원본 설정 출처"><p>{s.settings.parameter_source}</p><p>{s.settings.environment_source}</p>{s.settings.notes.map(note=><p key={note}>{note}</p>)}</HelpDisclosure></Panel></div>
 <JobLog/><CheckpointPanel/>
 </div>;
}
