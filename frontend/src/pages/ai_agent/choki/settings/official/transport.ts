
export const nativePrefix='/api/ai_agent/choki/native';
export function officialAssetUrl(path:string){return nativePrefix+path}

/** Keep official dialogs in the platform's font/color scope after portaling. */
export function officialPortalRoot(){
 let root=document.getElementById('hermes-official-overlays');
 if(!root){root=document.createElement('div');root.id='hermes-official-overlays';root.className='hermes-official ha-official-overlay-host';document.body.append(root)}
 return root;
}

/** Preserve the official HTTP protocol on the registered menu's API surface. */
export const officialFetch:typeof fetch=async(input,init)=>{
 const original=input instanceof Request?new Request(input,init):new Request(new URL(input.toString(),location.origin),init);
 const url=new URL(original.url);
 if(url.origin===location.origin&&!url.pathname.startsWith(nativePrefix)&&
    (url.pathname.startsWith('/api/')||url.pathname.startsWith('/dashboard-plugins/'))){
  url.pathname=nativePrefix+url.pathname;
  return globalThis.fetch(new Request(url,original));
 }
 return globalThis.fetch(original);
};
Object.assign(window,{__HERMES_BASE_PATH__:nativePrefix});

/** Native WebSocket semantics, carried over one authenticated platform socket. */
export function officialSocketUrl(input:string|URL){
 const native=new URL(input,location.href);
 if(native.host!==location.host)return native.href;
 if(!native.pathname.startsWith(nativePrefix))native.pathname=nativePrefix+native.pathname;
 native.protocol=location.protocol==='https:'?'wss:':'ws:';
 return native.href;
}
export class OfficialWebSocket extends WebSocket{
 constructor(url:string|URL,protocols?:string|string[]){super(officialSocketUrl(url),protocols)}
}
Object.assign(window,{ChokiPlatform:{fetch:officialFetch,WebSocket:OfficialWebSocket}});
