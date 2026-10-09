export interface LibraryExpert {
 id:string;name:string;role:'market'|'action';parameters?:number;feature_size:number;
 executor?:string;representation?:string;weight_bytes?:number;quantized?:boolean;
 conversion?:{source_id:string;source_sha256:string;precision:string;layers:number;original_tensor_bytes:number;converted_tensor_bytes:number;execution:string;comparison?:unknown;validation?:{passed:boolean;mode?:string;reference_passed?:boolean;relative_rmse:number;action_agreement:number|null;direction_agreement?:number|null;max_relative_rmse:number;min_action_agreement:number}};
 package:{file:string;sha256:string;bytes:number};
 input:{supported:boolean;pipeline:string;requires?:string[];universe?:string[];reason?:string};
 check:{status:string;detail:string;tested?:number;seconds?:number;metrics?:{device?:string;device_reason?:string;peak_ram_bytes?:number;peak_vram_bytes?:number}};
}
export interface DiscoveredExpert {id:string;repository:string;revision:string;url:string;source?:string;updated?:string;created?:string;release_date?:string;release_source?:string;downloads:number;compatible:boolean;same_weights?:boolean;template?:string;template_name?:string;bytes?:number;detail:string;
 installed_versions?:{id:string;name:string;revision:string|null;active:boolean}[];input_summary?:string;api_requirement?:string;requirements_verified?:boolean;domain?:string;overlap?:string[];overlap_basis?:string;resource_note?:string;input_evidence?:{source:string;snippets:string[];unavailable?:boolean}}
export interface Discovery {query:string;keywords?:string[];recent_days?:number;errors?:{query:string;detail:string}[];models:DiscoveredExpert[];scope:string}
export interface Inspection {completed:number;total:number;passed?:number;failed?:number;quality_warning?:number;started?:number;finished?:number;reports:{id:string;name:string;status:string;detail:string}[]}
export interface OptimizationReport {id:string;precision:string;passed:boolean;detail?:string;score?:number;eligible?:boolean;decision?:string;reason?:string;bytes?:number;package_available?:boolean;relative_rmse?:number;direction_agreement?:number|null;action_agreement?:number|null;measurement?:{warm_median_seconds?:number;cold_seconds?:number;metrics?:{device?:string;device_reason?:string;peak_ram_bytes?:number;peak_vram_bytes?:number}}}
export interface Optimization {replacement_required?:boolean;detail?:string;stage:string;goal:string;selected?:string;previous?:string;applied?:boolean;error?:string;started?:number;finished?:number;input_as_of?:string;reports?:OptimizationReport[];failures?:{precision:string;detail:string}[];attempts?:Record<string,{status:string;detail:string;id?:string}>}
export interface LibraryState {
 catalog:{experts?:Record<string,LibraryExpert>;active?:string[];installed?:Record<string,string>;updated?:number;comparison?:unknown;discovery?:Discovery;inspection?:Inspection;optimizations?:Record<string,Optimization>};
 job:{busy?:boolean;stage?:string;kind?:string;detail?:string;error?:string;completed?:number;total?:number;
      result?:{source?:string;check?:LibraryExpert['check'];experts?:{id:string;name:string;input:LibraryExpert['input'];native_template?:boolean}[]}};
}
