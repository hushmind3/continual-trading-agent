import {useEffect,useState} from 'react';
import {request} from '../../../../data/api';
import {Button,ErrorMessage} from '../../../../ui/Primitives';
import {prefix,failure,contentText} from '../types';
interface Skill {name:string;description:string;category?:string}
export function Skills(){
 const [rows,setRows]=useState<Skill[]>([]),[query,setQuery]=useState(''),[selected,setSelected]=useState(''),[detail,setDetail]=useState(''),[error,setError]=useState(''),[pending,setPending]=useState(false),[reload,setReload]=useState(0);
 useEffect(()=>{let live=true;setPending(true);void request<{skills:Skill[]}>(prefix+'skills',{},'GET').then(v=>{if(live){setRows(v.skills??[]);setError('')}}).catch(e=>{if(live)setError(failure(e))}).finally(()=>{if(live)setPending(false)});return()=>{live=false}},[reload]);
 const choose=async(name:string)=>{setSelected(name);setDetail('');setPending(true);setError('');try{const result=await request<Record<string,unknown>>(prefix+'skill',{name},'GET');if(result.success===false)throw new Error(String(result.error??result.message??'스킬 읽기 실패'));setDetail(contentText(result.content??result.skill??result))}catch(e){setError(failure(e))}finally{setPending(false)}};
 const visible=rows.filter(r=>(r.name+' '+r.description+' '+r.category).toLowerCase().includes(query.toLowerCase()));
 return <section className="hermes-settings"><div className="hermes-section-heading"><div><h3>스킬</h3><p className="hermes-muted">Hermes가 필요할 때 찾아 읽는 작업 지침 · {rows.length}개</p></div><Button disabled={pending} busy={pending} onClick={()=>setReload(v=>v+1)}>목록 갱신</Button></div><input aria-label="스킬 검색" placeholder="이름·설명 검색" value={query} onChange={e=>setQuery(e.target.value)}/><ErrorMessage message={error}/><div className="hermes-skills-layout"><div className="hermes-skill-list">{visible.map(skill=><button type="button" key={skill.category+'/'+skill.name} disabled={pending} aria-pressed={selected===skill.name} onClick={()=>void choose(skill.name)}><b>{skill.name}</b><small>{skill.category}</small><span>{skill.description}</span></button>)}{!visible.length&&!pending&&<p className="hermes-muted">해당 스킬이 없습니다.</p>}</div><article className="hermes-skill-detail"><h4>{selected||'스킬을 선택하세요'}</h4><pre>{detail}</pre></article></div></section>;
}
