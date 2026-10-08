import type {LibraryExpert} from '../../data/library';
export function expertFamilies(items:LibraryExpert[]){
 const grouped=new Map<string,LibraryExpert[]>();
 for(const item of items){const root=item.conversion?.source_id??item.id;grouped.set(root,[...grouped.get(root)??[],item])}
 return [...grouped.entries()].map(([id,variants])=>({id,base:variants.find(v=>v.id===id)??variants[0],variants}));
}
