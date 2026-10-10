import type {Expert} from '../../data/types';
import {Button} from '../../ui/Primitives';
import {bytes} from '../../ui/format';
export function ExpertVariants({variants,selected,active,onSelect}:{variants:Expert[];selected:string;active:string[];onSelect:(id:string)=>void}){
 return <div role="group" aria-label="Expert 정밀도 버전" className="flex flex-wrap gap-2">{variants.map(v=><Button key={v.id} aria-pressed={selected===v.id} className={'!px-3 !py-3 !text-xs '+(selected===v.id?'!bg-blue-50 !text-blue-700 ring-1 ring-blue-200':'!bg-slate-50')} onClick={()=>onSelect(v.id)}><span><strong className="block">{v.representation||'원본'}</strong><small className="mt-1 block text-slate-400">{bytes(v.weight_bytes??v.package.bytes)}</small><small className="mt-1 block">{active.includes(v.id)?'사용 중':v.package_available?'보관':'파일 없음'}</small></span></Button>)}</div>;
}
