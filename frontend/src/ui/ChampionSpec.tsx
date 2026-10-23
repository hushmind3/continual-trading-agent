import type {Champion} from '../data/library';
import {KeyValues} from './Panel';
import {bytes,number} from './format';
const spaceLabels:Record<string,string>={observation_shape:'관측 차원',action_shape:'행동 차원',actor_action_shape:'Actor 출력',critic_output_shapes:'Critic 출력',target_critic_output_shapes:'Target Critic 출력',value_output_shape:'가치 출력',log_prob_shape:'행동 확률 출력'};
const architectureLabels:Record<string,string>={market_hidden_size:'시장 Latent',market_attention_heads:'시장 Attention Heads',market_key_value_heads:'시장 KV Heads',market_head_dim:'Head 차원',market_ffn_size:'시장 FFN',policy_adapter_size:'정책 Adapter',policy_attention_heads:'정책 Attention Heads',expert_native_output_features:'Expert 출력',account_context_features:'계좌 입력',policy_feature_size:'정책 입력'};
export function ChampionSpec({model}:{model:Champion}){return <div className="space-y-3 text-sm">
 <p className="font-semibold">{model.identity.algorithm.toUpperCase()} · {model.name} · {model.trained?'학습 기록 있음':'미학습'} · {model.identity.currency}</p>
 <KeyValues items={[
  ['통합 PT 크기',bytes(model.file_bytes)],['중앙 정책 파라미터',number(model.parameters.central_parameters,0)],
  ['MoE 결합부 파라미터',number(model.parameters.integration_parameters,0)],['Frozen Expert 파라미터',number(model.parameters.expert_logical_parameters,0)],
  ['전체 논리 파라미터',number(model.parameters.total_logical_parameters,0)],['Expert 저장 가중치',bytes(model.parameters.expert_stored_tensor_bytes)],
  ['학습 단계',number(model.training?.num_timesteps,0)],['가중치 업데이트',number(model.training?.updates,0)],
  ...Object.entries(model.policy_spaces??{}).map(([key,value])=>[spaceLabels[key]??key,JSON.stringify(value)] as [string,string]),
  ...Object.entries(model.moe_architecture??{}).map(([key,value])=>[architectureLabels[key]??key,number(value,0)] as [string,string])
 ]}/>
 <p className="break-words text-xs text-slate-500">Expert {model.identity.champion_experts.length}개: {model.identity.champion_experts.join(' · ')||'중앙 정책만 포함'}</p>
 <details className="text-xs text-slate-500"><summary className="cursor-pointer">운영 종목 {model.identity.symbols.length}개 · 저장 경로</summary><p className="mt-2 break-words">{model.identity.symbols.join(' · ')}</p><p className="mt-2 break-all">{model.path}</p><p className="mt-1 break-all">{model.checkpoint}</p></details>
 </div>}
