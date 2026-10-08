export type Control = "feed" | "engine" | "paper" | "learning";
export type Currency = "USD" | "KRW";
export interface Worker {
  alive?: boolean;
  requested?: boolean;
  status?: string;
  pid?: number | null;
  version?: number;
  source_updates?: number;
  optimizer_steps?: number;
  error?: string;
  message?: string;
  heartbeat?: number;
  rss_bytes?: number;
  peak_ram_bytes?: number;
  decision_seconds?: number;
  last_as_of?: string;
  active_expert?: string | null;
  inference_seconds?: number;
  loss?: number;
  samples?: number;
  last_update?: {version:number;samples:number;optimizer_steps?:number;updated_at?:number};
  samples_per_second?: number;
  seconds?: number;
  expert_count?: number;
  retries?: number;
  device?: string;
}
export interface Expert {
  id: string;
  name: string;
  role?: string;
  frozen?: boolean;
  enabled?: boolean;
  status?: string;
  error?: string | null;
  parameters?: number;
  symbols?: string[] | null;
  universe?: string[] | null;
  load_seconds?: number;
  inference_seconds?: number;
  device?: string;
  peak_vram_bytes?: number;
  peak_ram_bytes?: number;
  last_as_of?: string;
  weight_files?: string[];
  job_seconds?: number;
}
export interface Decision {
  symbol: string;
  currency: Currency;
  action: string;
  target_weight: number;
  current_weight: number;
  as_of: string;
  order_queued?: boolean;
}
export interface Position {
  symbol: string;
  name?: string;
  quantity: number;
  average_cost: number;
  mark: number;
  value: number;
  pnl: number;
}
export interface Book {
  initial_cash: number;
  cash: number;
  equity: number;
  pnl: number;
  return_rate: number;
  positions: Position[];
  fees: number;
  slippage: number;
  spread: number;
  sell_tax: number;
  trade_count: number;
  recorded_fills: number;
  missing_fills: number;
}
export interface Fill {
  sequence: number;
  symbol: string;
  currency: Currency;
  action: string;
  price: number;
  quantity: number;
  date?: string;
  fee?: number;
  slippage?: number;
}
export interface Revision {
  file: string;
  version: number;
  time: number;
  bytes: number;
  sha256: string;
}
export interface OpsSettings {
  runtime: string;
  instruments: string;
  expert_checkpoint: string;
  enabled_experts: string[];
  learning: {
    batch_size: number;
    minimum_batch_size: number;
    batch_wait_seconds: number;
    epochs: number;
    learning_rate: number;
    discount: number;
    clip_epsilon: number;
    max_policy_lag: number;
    checkpoint_seconds: number;
    cpu_threads: number;
  };
  resources: {
    ram_reserve_gib: number;
    vram_reserve_gib: number;
    expert_cache_count: number;
    isolated_expert_parameters: number;
    expert_devices: Record<string,"cpu"|"auto"|"cuda:0">;
    market_refresh_seconds: number;
    inference_timeout_seconds: number;
    journal_limit_mib: number;
    retained_transitions: number;
    revisions: number;
    disk_reserve_gib: number;
    market_queue_batches: number;
  };
  risk: {
    freshness_seconds: number;
    fee: number;
    slippage: number;
  };
}
export interface Event {
  id: number;
  time: number;
  kind: string;
  detail: string;
  read: boolean;
}
export interface Snapshot {
  library?:import('./library').LibraryState;
  architecture: string;
  time: number;
  controls: Record<Control, boolean> & { mode: string };
  workers: Record<string, Worker>;
  agent: Worker;
  learner: Worker;
  training?: {code:string;label:string;detail:string;ready:number;required:number;remaining:number;pending:number;action:Control|null};
  experts: Expert[];
  account: {
    books: Record<Currency, Book>;
    fills: Fill[];
    pending: Record<string, unknown>;
  } | null;
  decisions: Decision[];
  feed: Record<string, unknown>;
  replay: {
    total: number;
    completed: number;
    outdated: number;
    ready: number;
    batch_ready: number;
    groups: {assets: number | null;ready: number}[];
    pending: number;
    bytes: number;
  };
  resources: {
    cpu_percent: number;
    ram_total_bytes: number;
    ram_available_bytes: number;
    ram_used_bytes: number;
    disk_free_bytes: number;
    gpu: {
      name?: string;
      utilization_percent?: number;
      used_bytes?: number;
      total_bytes?: number;
    };
    processes: {
      role: string;
      pid: number;
      rss_bytes: number;
      cpu_percent: number;
      threads: number;
      read_bytes: number;
      write_bytes: number;
    }[];
  };
  events: Event[];
  provider: {
    provider: string;
    provider_name?: string;
    environment: string;
    saved: boolean;
    has_app_key: boolean;
    has_secret: boolean;
    last_test?: { ok: boolean; message?: string; time?: string };
    vault_error?: string;
  };
  revisions: Revision[];
  current_policy?:Revision|null;
  settings: OpsSettings;
  equity_history: Record<
    Currency,
    { as_of: string; equity: number; cash: number; costs: number }[]
  >;
  real_orders_enabled: boolean;
}
export interface Instrument {
  symbol: string;
  name?: string;
  market: string;
  asset_class: string;
  required_by?: string[];
  latest_tick?:{date:string;price:number;provider:string}|null;
  quote?: {
    date: string;
    close: number;
    open: number;
    high: number;
    low: number;
    volume: number;
  } | null;
  decision?: Decision | null;
  history: { time: string; close: number }[];
}
