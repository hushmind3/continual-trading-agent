import {useOperations} from '../../data/Operations';
import {Panel,KeyValues} from '../../ui/Panel';
export function PolicyArchitecture(){const {state:s}=useOperations();if(!s)return null;const p=s.settings.policy;
 return <Panel title="Actor · Twin Critic · Target Critic" description="설치된 공식 SACPolicy 기본 구조 · 저장본 구조와 구분">
 <div className="grid gap-3 sm:grid-cols-3">{[['Actor',p.actor_arch.join(' → ')],['Twin Critic',p.critic_arch.join(' → ')+' · '+p.n_critics+' critics'],['Target Critic','SB3의 target update 경로']].map(([name,value])=><div key={name} className="rounded-xl bg-violet-50 p-4"><b className="text-sm text-violet-800">{name}</b><p className="mt-2 text-xs text-violet-600">{value}</p></div>)}</div>
 <KeyValues items={[['활성 함수',p.activation],['Optimizer',p.optimizer],['기본 Feature Extractor',p.feature_extractor],['Expert 연결',s.settings.observation],['저장 정책 관측 차원',s.model.observation_shape?.join(' × ')||'없음'],['저장 정책 행동 차원',s.model.action_shape?.join(' × ')||'없음']]}/>
 <p className="mt-4 text-xs leading-6 text-slate-500">모든 SAC 경로가 PortfolioOptimizationEnv의 가격 관측, Frozen Expert별 실제 출력 64D, 계좌 16D를 동일한 ChampionExtractor에 전달합니다. 중앙 SAC Actor·Twin Critic이 현금과 종목별 목표 비중을 결정합니다.</p>
 </Panel>;
}
