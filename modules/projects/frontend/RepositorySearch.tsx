import {useState,type FormEvent} from 'react';
import {Download,Search,Star} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,Input,ErrorMessage,Empty} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import type {Repository} from './types';
export function RepositorySearch({install,busy}:{install:(url:string)=>void;busy:boolean}){
 const [url,setUrl]=useState(''),[query,setQuery]=useState(''),[results,setResults]=useState<Repository[]>([]),[searched,setSearched]=useState(false),[searching,setSearching]=useState(false),[error,setError]=useState('');
 async function search(event:FormEvent){event.preventDefault();setSearching(true);setError('');try{const data=await request<{items:Repository[]}>('projects/search',{q:query},'GET');setResults(data.items);setSearched(true)}catch(e){setError(String(e))}finally{setSearching(false)}}
 return <div className="space-y-6">
  <Panel title="GitHub 주소로 등록"><form className="flex flex-col gap-3 sm:flex-row" onSubmit={e=>{e.preventDefault();install(url)}}><Input aria-label="GitHub 저장소 주소" placeholder="https://github.com/소유자/저장소" value={url} onChange={e=>setUrl(e.target.value)} required/><Button tone="primary" type="submit" disabled={busy||!url.trim()}><Download size={16}/>등록</Button></form><p className="mt-3 text-sm text-slate-500">다운로드부터 구조 분석·설치·실행 확인까지 이어집니다. 원래 화면이 있으면 그대로 연결합니다.</p></Panel>
  <Panel title="GitHub 검색"><form className="flex gap-3" onSubmit={search}><Input aria-label="GitHub 검색어" placeholder="어떤 프로젝트가 필요한가요?" value={query} onChange={e=>setQuery(e.target.value)} required/><Button type="submit" busy={searching}><Search size={16}/>검색</Button></form><ErrorMessage message={error}/>
   <div className="mt-5 grid gap-4 lg:grid-cols-2">{results.map(repo=><article className="flex min-w-0 flex-col gap-3 rounded-xl border border-slate-200 p-4" key={repo.repository}><div className="flex items-start justify-between gap-3"><a className="break-all font-semibold text-slate-900 hover:underline" href={repo.url} target="_blank" rel="noreferrer">{repo.repository}</a><Button disabled={busy} onClick={()=>install(repo.url)}>등록</Button></div><p className="text-sm leading-6 text-slate-600">{repo.description||'저장소 설명이 없습니다.'}</p><div className="mt-auto flex flex-wrap items-center gap-4 text-xs text-slate-500"><span className="inline-flex items-center gap-1"><Star size={13}/>{repo.stars.toLocaleString()}</span><span>{repo.language}</span><span>{new Date(repo.updated_at).toLocaleDateString('ko-KR')} 업데이트</span></div></article>)}</div>
   {searched&&!results.length&&<Empty title="검색 결과가 없습니다." detail="검색어를 바꾸거나 저장소 주소로 등록하세요."/>}
  </Panel>
 </div>;
}
