export type Currency = "USD" | "KRW";
export type Control = "learning";
export interface Worker {alive?:boolean;requested?:boolean;status?:string;error?:string}
export interface FileState {exists:boolean;bytes:number;modified:string|null}
export interface Instrument {
  symbol:string;name:string;currency:Currency;market:string;eligible:boolean;stored:boolean;
  rows:number;observations:number;trading_days:number;start:string|null;end:string|null;last_close:number|null;
}
export interface Bar {date:string;open:number|null;high:number|null;low:number|null;close:number|null;volume:number|null}
export interface Expert {
  id:string;name:string;role:"market"|"action";active:boolean;package_available:boolean;package_path:string;
  representation?:string;executor?:string;backend?:string;category?:"forecast"|"trading"|"interpretation";
  parameters?:number;feature_size:number;weight_bytes?:number;quantized?:boolean;
  package:{file:string;bytes:number;sha256:string};
  conversion?:{source_id:string;precision?:string;original_tensor_bytes?:number;converted_tensor_bytes?:number;layers?:number;native_forward_layers?:number;validation?:{passed?:boolean;relative_rmse?:number;max_relative_rmse?:number;action_agreement?:number;direction_agreement?:number;min_action_agreement?:number};comparison?:unknown};
  input:{supported:boolean;pipeline:string;requires?:string[];universe?:string[];minimum_history?:number;reason?:string};
  inference?:{status:string;reason?:string;as_of?:string;output?:number[]};
  check?:{status:string;detail?:string;tested?:number;seconds?:number;metrics?:Record<string,unknown>};
  resources:Record<string,unknown>;origin?:string|Record<string,unknown>;
  current_resources?:Record<string,unknown>;loaded?:boolean;
}
export interface Job {
  running:boolean;id?:string;status?:string;command?:string;pid?:number;started_at?:string;finished_at?:string;
  exit_code?:number;log_text:string;detail?:string;currency?:Currency;symbols?:string[];
  measurements:Record<string,number>;
}
export interface Checkpoint {name:string;path:string;file:FileState;num_timesteps:number|null;updates:number|null;identity:Record<string,unknown>;compatible:boolean}
export interface Snapshot {
  architecture:"finrlx-official-sac-v2";updated_at:string;
  settings:{
    parameters:Record<string,string|number|boolean>;steps_per_run:number;environment:string;
    environment_args:Record<string,number>;covariance_lookback:number;rolling_days:number[];
    parameter_source:string;environment_source:string;save_policy:string;observation:string;notes:string[];
    sb3_defaults:Record<string,unknown>;policy:{actor_arch:number[];critic_arch:number[];n_critics:number;activation:string;optimizer:string;feature_extractor:string};
    versions:Record<string,string>;
  };
  model:{file:FileState;replay:FileState;identity:{currency?:Currency;symbols?:string[]};compatible:boolean;reasons:string[];
    num_timesteps:number|null;updates:number|null;observation_shape?:number[];action_shape?:number[];
    parameters?:Record<string,unknown>;replay_state:{status:string;error?:string;size?:number;capacity?:number;position?:number;full?:boolean;n_envs?:number;array_bytes?:number}};
  data:{path?:string;error:string|null;rows:number;tickers:number;start?:string;end?:string;instruments:Instrument[]};
  experts:{active:string[];items:Expert[];as_of?:string;reported?:string;observation_connection:{size:number;configured:boolean;last_success:{market:number;action:number};recorded:boolean}};
  job:Job;evaluation:{points:{date:string;value:number}[];file:FileState;report:{currency?:Currency;symbols?:string[];strategies?:Record<string,Record<string,number|null>>}};
  resources:{cpu_percent:number;ram_total_bytes:number;ram_used_bytes:number;ram_available_bytes:number;disk_free_bytes:number;
    gpu:{name?:string;total_bytes?:number;used_bytes?:number;utilization_percent?:number;error?:string};
    processes:{role:string;pid:number;rss_bytes:number;cpu_percent:number;threads:number;read_bytes:number;write_bytes:number}[]};
  checkpoints:Checkpoint[];
  operations?:OperationsState;
  library?:{job:{busy:boolean;stage?:string;kind?:string;error?:string;detail?:string;result?:any;completed?:number;total?:number;finished?:number};
    catalog:{active?:string[];experts?:Record<string,Expert>;comparison?:unknown;discovery?:{models:DiscoveryModel[];query?:string;keywords?:string[];errors?:{query:string;detail:string}[];scope?:string;recent_days?:number};optimizations?:Record<string,any>;quantizations?:Record<string,any>}};
  automation?:AutomationState;
  capabilities:Record<string,{status:"supported"|"not_connected"|"removed"|"requires_configuration";reason:string;source:string}>;
}
export interface Preflight {ok:boolean;errors:string[];symbols:string[];currency:Currency;mode:string;steps_per_run:number;periods:{training_observations:number;test_observations:number;train_start:string;train_end_exclusive:string}|null}
export interface ResultTable {columns:string[];rows:Record<string,unknown>[];total:number}
export interface Connections {api:{status:string};data:{status:string;source:string|null;available_sources:string[];reason?:string};brokers:{name:string;status:string;reason:string}[]}
export interface OperationsState {
  controls:{feed:boolean;paper:boolean;engine:boolean};
  account:{books:Record<Currency,{initial_cash:number;cash:number;equity:number;net_pnl:number;
    holdings_value:number;fees:number;realized_pnl:number;trade_count:number;
    positions:Record<string,{quantity:number;average_cost:number}>;marks:Record<string,number>}>;
    fills:Record<string,unknown>[];pending:Record<string,unknown>};
  quotes:Record<string,Record<string,unknown>>;decisions:Record<string,unknown>[];
  feed:{status:string;error?:string;policy_error?:string;last_as_of?:string};
  broker?:{connected?:boolean;last_error?:string;last_message_utc?:string};
  pool:{id:string;loaded?:boolean;device?:string;resident_bytes?:number;peak_ram_increment?:number}[];
}
export interface DiscoveryModel {id:string;repository:string;compatible:boolean;same_weights?:boolean;
  detail?:string;bytes?:number;url:string;source?:string;domain?:string;downloads?:number;
  created?:string;updated?:string;release_date?:string;release_source?:string;revision?:string;
  resource_note?:string;api_requirement?:string;input_summary?:string;
  overlap?:string[];overlap_basis?:string;requirements_verified?:boolean;
  template_name?:string;installed_versions?:{name:string;revision?:string;active?:boolean}[];
  input_evidence?:{source?:string;snippets?:string[]};
}
export interface OperationStage {id:string;title:string;status:'pending'|'running'|'complete'|'failed'|'blocked';detail?:string;log_path?:string;log?:string}
export interface OperationProgress {status:string;active?:boolean;applied?:boolean;detail?:string;error?:string;stages:OperationStage[];checks?:OperationStage[];changed_files?:string[];currencies?:string[]}
export interface AutomationState {apply:OperationProgress;system:OperationProgress}
