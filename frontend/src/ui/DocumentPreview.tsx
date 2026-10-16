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

type OpenDocument={path:string;load:(path:string)=>Promise<PreviewDocument>;origin:HTMLElement|null;document?:PreviewDocument};
const DocumentContext=createContext<{current?:OpenDocument;show:(value:OpenDocument)=>Promise<void>;close:()=>void}|null>(null);
export function DocumentWorkspace({children}:{children:ReactNode}){
 const [current,setCurrent]=useState<OpenDocument>(),sequence=useRef(0);
 const show=async(value:OpenDocument)=>{const id=++sequence.current;const document=await value.load(value.path);if(id===sequence.current)setCurrent({...value,document})};
 const close=()=>{sequence.current++;current?.origin?.focus();setCurrent(undefined)};
 return <DocumentContext.Provider value={{current,show,close}}>{children}</DocumentContext.Provider>;
}
export function useDocumentWorkspace(){return useContext(DocumentContext)}
export function DocumentPreview({path,children,load}:{path:string;children?:ReactNode;load:(path:string)=>Promise<PreviewDocument>}){
 const workspace=useDocumentWorkspace(),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const show=async(origin:HTMLElement)=>{setLoading(true);setError('');try{await workspace?.show({path,load,origin})}catch(error){setError(error instanceof Error?error.message:String(error))}finally{setLoading(false)}};
 return workspace?<><Button type="button" className="h-auto px-1 py-0 text-left" busy={loading} disabled={loading} onClick={event=>void show(event.currentTarget)}>{children||path.split(/[\\/]/).at(-1)}</Button>{error&&<span role="alert" className="block text-sm text-red-600">{error}</span>}</>:<PopupPreview path={path} load={load}>{children}</PopupPreview>;
}
export function DocumentPanel(){
 const workspace=useDocumentWorkspace(),current=workspace?.current,document=current?.document;
 const [source,setSource]=useState(false),[compact,setCompact]=useState(false),panel=useRef<HTMLElement>(null);
 useEffect(()=>{setSource(false)},[current]);
 useEffect(()=>{if(!current)return;const key=(event:KeyboardEvent)=>{if(event.key==='Escape')workspace?.close()};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[workspace,current]);
 if(!document)return null;
 const resize=(clientX:number)=>{const element=panel.current,parent=element?.parentElement;if(!element||!parent)return;const bounds=parent.getBoundingClientRect();const width=Math.min(70,Math.max(30,(bounds.right-clientX)/bounds.width*100));element.style.setProperty('--document-width',width+'%')};
 return <aside ref={panel} className={'hermes-document-panel '+(compact?'is-compact':'')} aria-label="결과 문서"><div role="separator" aria-label="문서 너비 조절" aria-orientation="vertical" tabIndex={0} className="hermes-document-resizer" onPointerDown={event=>{event.currentTarget.setPointerCapture(event.pointerId)}} onPointerMove={event=>{if(event.currentTarget.hasPointerCapture(event.pointerId))resize(event.clientX)}} onKeyDown={event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();const bounds=panel.current?.getBoundingClientRect();if(bounds)resize(bounds.left+(event.key==='ArrowLeft'?-20:20))}}}/><header className="flex min-w-0 items-center justify-between gap-2 border-b p-3"><strong className="min-w-0 truncate" title={document.path}>{document.name}</strong><div className="flex shrink-0 gap-1"><Button aria-label={compact?'문서 패널 확대':'문서 패널 축소'} onClick={()=>{panel.current?.style.removeProperty('--document-width');setCompact(value=>!value)}}>{compact?'확대':'축소'}</Button><Button onClick={()=>setSource(value=>!value)}>{source?'문서':'소스'}</Button><Button aria-label="문서 닫기" onClick={workspace?.close}>닫기</Button></div></header><div className="min-h-0 flex-1 overflow-auto p-5">{document.truncated&&<p>큰 문서의 앞 1 MiB만 표시합니다.</p>}{document.format==='.md'&&!source?<div className="ha-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{img:({alt})=><span>{alt}</span>}}>{document.content}</Markdown></div>:<pre className="whitespace-pre-wrap break-words text-sm">{document.content}</pre>}</div></aside>;
}
