export interface LibraryExpert {
 id:string;name:string;role:'market'|'action';parameters?:number;feature_size:number;
 executor?:string;representation?:string;
 package:{file:string;sha256:string;bytes:number};
 input:{supported:boolean;pipeline:string;requires?:string[];universe?:string[];reason?:string};
 check:{status:string;detail:string;tested?:number;seconds?:number;metrics?:{peak_ram_bytes?:number;peak_vram_bytes?:number}};
}
export interface LibraryState {
 catalog:{experts?:Record<string,LibraryExpert>;active?:string[];installed?:Record<string,string>;updated?:number;comparison?:unknown};
 job:{busy?:boolean;stage?:string;kind?:string;detail?:string;error?:string;completed?:number;total?:number;
      result?:{source?:string;experts?:{id:string;name:string;input:LibraryExpert['input'];native_template?:boolean}[]}};
}
