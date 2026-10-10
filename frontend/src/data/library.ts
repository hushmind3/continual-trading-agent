import type {Expert} from './types';
export type LibraryExpert=Expert;
export interface DiscoveredExpert {
  id:string;repository:string;compatible:boolean;same_weights?:boolean;detail?:string;bytes?:number;url:string;
  source?:string;domain?:string;downloads?:number;created?:string;updated?:string;release_date?:string;
  release_source?:string;revision?:string;resource_note?:string;api_requirement?:string;input_summary?:string;
  overlap?:string[];overlap_basis?:string;requirements_verified?:boolean;template_name?:string;
  installed_versions?:{name:string;revision?:string;active?:boolean}[];input_evidence?:{source?:string;snippets?:string[]};
}
export interface OptimizationReport {
  id:string;precision?:string;passed?:boolean;eligible?:boolean;bytes?:number;reason?:string;detail?:string;
  score?:number;relative_rmse?:number;action_agreement?:number|null;direction_agreement?:number|null;
  measurement?:{cold_seconds?:number;warm_median_seconds?:number;metrics?:{device?:string;peak_ram_bytes?:number;peak_vram_bytes?:number}};
}
export interface Optimization {stage?:string;goal?:string;selected?:string;previous?:string;input_as_of?:string;started?:number;finished?:number;reports?:OptimizationReport[];attempts?:Record<string,{status?:string;detail?:string}>;failures?:{precision:string;detail:string}[];detail?:string;error?:string;applied?:boolean}
export interface Inspection {started?:number;finished?:number;reports?:{id:string;status:string;detail?:string}[]}
export interface LibraryState {catalog:{active?:string[];experts?:Record<string,LibraryExpert>;comparison?:unknown;discovery?:{models:DiscoveredExpert[];query?:string;keywords?:string[];errors?:{query:string;detail:string}[];scope?:string;recent_days?:number};optimizations?:Record<string,Optimization>};job:{busy:boolean;stage?:string;kind?:string;error?:string;detail?:string;result?:any;completed?:number;total?:number;finished?:number}}
