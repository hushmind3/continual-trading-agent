import type {LibraryExpert} from '../../data/library';
export const categoryNames={forecast:'시계열 예측',trading:'매매 판단',interpretation:'시장 해석'};
export function expertCategory(item:LibraryExpert){return item.category??(item.role==='action'?'trading':item.executor==='llama_cpp'||item.backend==='gguf_market'?'interpretation':'forecast')}
export function expertFamilies(items:LibraryExpert[]){
 const ids=new Set(items.map(item=>item.id));
 const rootOf=(item:LibraryExpert)=>{
  const source=item.conversion?.source_id;
  if(source&&ids.has(source))return source;
  const candidate=item.id.replace(/_(fp16|bf16|int8|int4|nf4)$/i,'');
  return candidate!==item.id&&ids.has(candidate)?candidate:item.id;
 };
 const grouped=new Map<string,LibraryExpert[]>();
 for(const item of items){const root=rootOf(item);grouped.set(root,[...grouped.get(root)??[],item])}
 return [...grouped.entries()].map(([id,variants])=>({id,base:variants.find(v=>v.id===id)??variants[0],variants:variants.sort((a,b)=>a.id===id?-1:b.id===id?1:a.id.localeCompare(b.id))})).sort((a,b)=>Object.keys(categoryNames).indexOf(expertCategory(a.base))-Object.keys(categoryNames).indexOf(expertCategory(b.base)));
}
