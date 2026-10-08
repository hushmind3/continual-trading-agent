export interface LibraryExpert {
 id:string;name:string;role:'market'|'action';parameters?:number;feature_size:number;
 executor?:string;representation?:string;
 conversion?:{source_id:string;source_sha256:string;precision:string;layers:number;original_tensor_bytes:number;converted_tensor_bytes:number;execution:string;comparison?:unknown;validation?:{passed:boolean;relative_rmse:number;action_agreement:number|null;direction_agreement?:number|null;max_relative_rmse:number;min_action_agreement:number}};
 package:{file:string;sha256:string;bytes:number};
 input:{supported:boolean;pipeline:string;requires?:string[];universe?:string[];reason?:string};
 check:{status:string;detail:string;tested?:number;seconds?:number;metrics?:{device?:string;device_reason?:string;peak_ram_bytes?:number;peak_vram_bytes?:number}};
}
export interface DiscoveredExpert {id:string;repository:string;revision:string;url:string;updated?:string;downloads:number;compatible:boolean;same_weights?:boolean;template?:string;template_name?:string;bytes?:number;detail:string}
export interface Discovery {query:string;models:DiscoveredExpert[];scope:string}
export interface Optimization {stage:string;goal:string;selected?:string;previous?:string;applied?:boolean;error?:string;reports?:{id:string;precision:string;passed:boolean;score?:number}[]}
export interface LibraryState {
 catalog:{experts?:Record<string,LibraryExpert>;active?:string[];installed?:Record<string,string>;updated?:number;comparison?:unknown;discovery?:Discovery;optimizations?:Record<string,Optimization>};
 job:{busy?:boolean;stage?:string;kind?:string;detail?:string;error?:string;completed?:number;total?:number;
      result?:{source?:string;check?:LibraryExpert['check'];experts?:{id:string;name:string;input:LibraryExpert['input'];native_template?:boolean}[]}};
}
