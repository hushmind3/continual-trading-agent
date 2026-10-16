import {useRef,useState,type FormEvent} from 'react';
import {Download,Search,Star} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,Input,Select,ErrorMessage,Empty} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import type {Repository} from './types';
import {useKorean} from './useKorean';
export function RepositorySearch({install,busy,allowAgent,setAllowAgent}:{install:(url:string)=>void;busy:boolean;allowAgent:boolean;setAllowAgent:(value:boolean)=>void}){
 const [url,setUrl]=useState(''),[query,setQuery]=useState(''),[results,setResults]=useState<Repository[]>([]),[searched,setSearched]=useState(false),[searching,setSearching]=useState(false),[error,setError]=useState('');
 const [sort,setSort]=useState(''),[page,setPage]=useState(0),[total,setTotal]=useState(0),[more,setMore]=useState(false),[incomplete,setIncomplete]=useState(false);
 const active=useRef({q:'',sort:''}),sequence=useRef(0);
 const [korean,setKorean]=useState(()=>localStorage.getItem('projects.korean')!=='false');
 const language=useKorean(results.map(repo=>repo.description),korean);
 async function load(next:number){const id=++sequence.current;setSearching(true);setError('');try{const data=await request<{items:Repository[];total:number;has_more:boolean;incomplete:boolean}>('projects/search',{...active.current,page:next},'GET');if(id!==sequence.current)return;setResults(previous=>next===1?data.items:[...previous,...data.items.filter(item=>!previous.some(old=>old.repository===item.repository))]);setPage(next);setTotal(data.total);setMore(data.has_more);setIncomplete(data.incomplete);setSearched(true)}catch(e){if(id===sequence.current)setError(String(e))}finally{if(id===sequence.current)setSearching(false)}}
 function search(event:FormEvent){event.preventDefault();active.current={q:query,sort};void load(1)}
 return <div className="space-y-6">
  <Panel title="GitHub 주소로 설치"><form className="flex flex-col gap-3 sm:flex-row" onSubmit={e=>{e.preventDefault();install(url)}}><Input aria-label="GitHub 저장소 주소" placeholder="https://github.com/소유자/저장소.git" value={url} onChange={e=>setUrl(e.target.value)} required/><Button tone="primary" type="submit" disabled={busy||!url.trim()}><Download size={16}/>설치</Button></form><p className="mt-3 text-sm text-slate-500">실행 방식을 찾아 설치하고 메뉴와 화면을 연결합니다. 지원하지 않는 구조를 성공으로 표시하지 않습니다.</p><label className="mt-3 flex items-center gap-2 text-sm"><Input type="checkbox" checked={allowAgent} onChange={e=>setAllowAgent(e.target.checked)}/>미지원 구조를 모델로 자동 변환</label><p className="mt-1 text-xs text-slate-500">기본은 모델을 사용하지 않습니다. 켜면 원본 Hermes가 로컬 모델을 불러와 이 앱 소스만 변환합니다.</p></Panel>
  <Panel title="GitHub 검색"><form className="flex flex-col gap-3 sm:flex-row" onSubmit={search}><Input aria-label="GitHub 검색어" placeholder="프로젝트 이름 · language:Python · topic:ai" value={query} onChange={e=>setQuery(e.target.value)} required/><Select aria-label="검색 정렬" value={sort} onChange={e=>setSort(e.target.value)}><option value="">관련도순</option><option value="stars">인기순</option><option value="updated">최근 업데이트순</option></Select><Button type="submit" busy={searching}><Search size={16}/>검색</Button></form><ErrorMessage message={error}/>
   {searched&&<p className="mt-3 text-sm text-slate-500">전체 {total.toLocaleString()}개 · {results.length}개 표시{incomplete?' · GitHub가 일부 결과만 반환했습니다.':''}</p>}
   <label className="mt-3 flex items-center gap-2 text-sm"><Input type="checkbox" checked={korean} onChange={e=>{setKorean(e.target.checked);localStorage.setItem('projects.korean',String(e.target.checked))}}/>설명을 자동으로 한국어 번역</label>{korean&&language.state==='pending'&&<p className="mt-2 text-xs text-slate-500">로컬 모델로 번역 중입니다. 설치는 바로 진행할 수 있습니다.</p>}{korean&&language.state==='unavailable'&&<p className="mt-2 text-xs text-slate-500">번역 대기 · {language.detail}</p>}
   <div className="mt-5 grid gap-4 lg:grid-cols-2">{results.map(repo=><article className="flex min-w-0 flex-col gap-3 rounded-xl border border-slate-200 p-4" key={repo.repository}><div className="flex items-start justify-between gap-3"><a className="break-all font-semibold text-slate-900 hover:underline" href={repo.url} target="_blank" rel="noreferrer">{repo.repository}</a><Button disabled={busy} onClick={()=>install(repo.url)}>설치</Button></div><p className="text-sm leading-6 text-slate-600" title={repo.description}>{language.text(repo.description)||'저장소 설명이 없습니다.'}</p><div className="mt-auto flex flex-wrap items-center gap-4 text-xs text-slate-500"><span className="inline-flex items-center gap-1"><Star size={13}/>{repo.stars.toLocaleString()}</span><span>{repo.language}</span><span>{new Date(repo.updated_at).toLocaleDateString('ko-KR')} 업데이트</span></div></article>)}</div>
   {searched&&!results.length&&<Empty title="검색 결과가 없습니다." detail="검색어를 바꾸거나 저장소 주소로 등록하세요."/>}
   {more&&<div className="mt-5 flex justify-center"><Button busy={searching} onClick={()=>void load(page+1)}>검색 결과 더 보기</Button></div>}
  </Panel>
 </div>;
}
