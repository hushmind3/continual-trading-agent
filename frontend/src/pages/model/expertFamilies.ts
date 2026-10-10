import type {LibraryExpert} from '../../data/library';
export const categoryNames={forecast:'시계열 예측',trading:'매매 판단',interpretation:'시장 해석'};
export function expertCategory(item:LibraryExpert){return item.category??(item.role==='action'?'trading':item.executor==='llama_cpp'||item.backend==='gguf_market'?'interpretation':'forecast')}
export function expertFamilies(items:LibraryExpert[]){
 const grouped=new Map<string,LibraryExpert[]>();
 for(const item of items){const root=item.conversion?.source_id??item.id;grouped.set(root,[...grouped.get(root)??[],item])}
 return [...grouped.entries()].map(([id,variants])=>({id,base:variants.find(v=>v.id===id)??variants[0],variants})).sort((a,b)=>Object.keys(categoryNames).indexOf(expertCategory(a.base))-Object.keys(categoryNames).indexOf(expertCategory(b.base)));
}
