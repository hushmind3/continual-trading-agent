import {useEffect,useRef,useState,type ReactNode} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {Button,Drawer,ErrorMessage} from './Primitives';

export interface PreviewDocument {name:string;path:string;format:string;bytes:number;content:string;truncated:boolean}
export function DocumentPreview({path,children,load}:{path:string;children?:ReactNode;load:(path:string)=>Promise<PreviewDocument>}){
 const [open,setOpen]=useState(false),[document,setDocument]=useState<PreviewDocument>(),[error,setError]=useState('');
 const sequence=useRef(0);useEffect(()=>()=>{sequence.current++},[]);
 const show=async()=>{const id=++sequence.current;setOpen(true);setDocument(undefined);setError('');try{const next=await load(path);if(sequence.current===id)setDocument(next)}catch(e){if(sequence.current===id)setError(e instanceof Error?e.message:String(e))}};
 return <><Button type="button" className="h-auto px-1 py-0 text-left" onClick={()=>void show()}>{children||path.split(/[\\/]/).at(-1)||path}</Button><Drawer title={document?.name||'문서 보기'} open={open} onClose={()=>{sequence.current++;setOpen(false)}}><ErrorMessage message={error}/>{!document&&!error&&<p role="status">문서를 불러오는 중입니다…</p>}{document&&<><p className="break-all text-sm">{document.path}</p>{document.truncated&&<p role="status">큰 문서의 앞 1 MiB만 표시합니다.</p>}{document.format==='.md'?<div className="ha-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{img:({alt})=><span>{alt||'이미지 참조'}</span>,a:({href,children})=><a href={href} target="_blank" rel="noreferrer">{children}</a>}}>{document.content}</Markdown></div>:<pre className="whitespace-pre-wrap break-words text-sm">{document.content}</pre>}</>}</Drawer></>;
}
