import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {Button,Drawer,ErrorMessage} from './Primitives';

export interface PreviewDocument {name:string;path:string;format:string;bytes:number;content:string;truncated:boolean}
function PopupPreview({path,children,load}:{path:string;children?:ReactNode;load:(path:string)=>Promise<PreviewDocument>}){
 const [open,setOpen]=useState(false),[document,setDocument]=useState<PreviewDocument>(),[error,setError]=useState('');
 const sequence=useRef(0);useEffect(()=>()=>{sequence.current++},[]);
 const show=async()=>{const id=++sequence.current;setOpen(true);setDocument(undefined);setError('');try{const next=await load(path);if(sequence.current===id)setDocument(next)}catch(e){if(sequence.current===id)setError(e instanceof Error?e.message:String(e))}};
 return <><Button type="button" className="h-auto px-1 py-0 text-left" onClick={()=>void show()}>{children||path.split(/[\\/]/).at(-1)||path}</Button><Drawer title={document?.name||'문서 보기'} open={open} onClose={()=>{sequence.current++;setOpen(false)}}><ErrorMessage message={error}/>{!document&&!error&&<p role="status">문서를 불러오는 중입니다…</p>}{document&&<><p className="break-all text-sm">{document.path}</p>{document.truncated&&<p role="status">큰 문서의 앞 1 MiB만 표시합니다.</p>}{document.format==='.md'?<div className="ha-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{img:({alt})=><span>{alt||'이미지 참조'}</span>,a:({href,children})=><a href={href} target="_blank" rel="noreferrer">{children}</a>}}>{document.content}</Markdown></div>:<pre className="whitespace-pre-wrap break-words text-sm">{document.content}</pre>}</>}</Drawer></>;
}

type OpenDocument={path:string;load:(path:string)=>Promise<PreviewDocument>;origin:HTMLElement|null};
const DocumentContext=createContext<{current?:OpenDocument;show:(value:OpenDocument)=>void;close:()=>void}|null>(null);
export function DocumentWorkspace({children}:{children:ReactNode}){
 const [current,show]=useState<OpenDocument>();
 const close=()=>{current?.origin?.focus();show(undefined)};
 return <DocumentContext.Provider value={{current,show,close}}>{children}</DocumentContext.Provider>;
}
export function useDocumentWorkspace(){return useContext(DocumentContext)}
export function DocumentPreview({path,children,load}:{path:string;children?:ReactNode;load:(path:string)=>Promise<PreviewDocument>}){
 const workspace=useDocumentWorkspace();
 return workspace?<Button type="button" className="h-auto px-1 py-0 text-left" onClick={event=>workspace.show({path,load,origin:event.currentTarget})}>{children||path.split(/[\\/]/).at(-1)}</Button>:<PopupPreview path={path} load={load}>{children}</PopupPreview>;
}
export function DocumentPanel(){
 const workspace=useDocumentWorkspace(),current=workspace?.current;
 const [document,setDocument]=useState<PreviewDocument>(),[error,setError]=useState(''),[source,setSource]=useState(false);
 useEffect(()=>{let alive=true;setDocument(undefined);setError('');setSource(false);if(current)void current.load(current.path).then(value=>{if(alive)setDocument(value)}).catch(error=>{if(alive)setError(String(error))});return()=>{alive=false}},[current]);
 useEffect(()=>{if(!current)return;const key=(event:KeyboardEvent)=>{if(event.key==='Escape')workspace?.close()};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[workspace,current]);
 if(!current)return null;
 return <aside className="hermes-document-panel" aria-label="결과 문서"><header className="flex items-center justify-between gap-2 border-b p-3"><strong className="min-w-0 truncate">{document?.name||current.path.split(/[\\/]/).at(-1)}</strong><div className="flex shrink-0 gap-2"><Button onClick={()=>setSource(value=>!value)}>{source?'문서 보기':'소스 보기'}</Button><Button aria-label="문서 닫기" onClick={workspace?.close}>닫기</Button></div></header><div className="min-h-0 flex-1 overflow-auto p-5"><ErrorMessage message={error}/>{!document&&!error&&<p role="status">문서를 불러오는 중입니다…</p>}{document&&<>{document.truncated&&<p>큰 문서의 앞 1 MiB만 표시합니다.</p>}{document.format==='.md'&&!source?<div className="ha-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{img:({alt})=><span>{alt}</span>}}>{document.content}</Markdown></div>:<pre className="whitespace-pre-wrap break-words text-sm">{document.content}</pre>}</>}</div></aside>;
}
