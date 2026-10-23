import {Button} from '@platform/ui/Primitives';
import {Children,isValidElement,memo,useState,type ReactNode} from 'react';
import Markdown,{defaultUrlTransform} from 'react-markdown';
import {DocumentLink,documentPath} from './DocumentLink';
import remarkGfm from 'remark-gfm';
import {displayEngineResponse} from './EngineNotes';
import {Check,Copy,TriangleAlert} from 'lucide-react';

export function CopyButton({text,label='복사'}:{text:string;label?:string}){
 const [state,setState]=useState<'idle'|'copied'|'error'>('idle');
 return <Button type="button" className="ha-copy" title={label} aria-label={state==='copied'?'복사됨':label} onClick={()=>{void navigator.clipboard.writeText(text).then(()=>{setState('copied');setTimeout(()=>setState('idle'),1800)}).catch(()=>setState('error'))}}>{state==='copied'?<Check size={14}/>:state==='error'?<TriangleAlert size={14}/>:<Copy size={14}/>}<span>{state==='copied'?'복사됨':state==='error'?'복사 실패':label}</span></Button>;
}
function CodeBlock({children}:{children?:ReactNode}){
 const child=Children.toArray(children)[0];
 const props=isValidElement<{children?:ReactNode;className?:string}>(child)?child.props:undefined;
 const code=String(props?.children??'').replace(/\n$/,'');
 const language=props?.className?.replace('language-','')??'코드';
 return <figure className="ha-code-block"><figcaption><span>{language}</span><CopyButton text={code} label="코드 복사"/></figcaption><pre>{children}</pre></figure>;
}
export const MessageBody=memo(function MessageBody({text,user=false,steered=false}:{text:string;user?:boolean;steered?:boolean}){
 if(user)return <div className="ha-user-text">{steered&&text.startsWith('[OUT-OF-BAND USER MESSAGE')&&text.endsWith('[/OUT-OF-BAND USER MESSAGE]')?text.split('\n').slice(1,-1).join('\n'):text}</div>;
 return <div className="ha-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml urlTransform={url=>documentPath(url)?url:defaultUrlTransform(url)} components={{
  pre:({children})=><CodeBlock>{children}</CodeBlock>,
  table:({children})=><div className="ha-table-scroll"><table>{children}</table></div>,
  a:({children,href})=>href&&documentPath(href)?<DocumentLink path={href}>{children}</DocumentLink>:<a href={href} target="_blank" rel="noreferrer">{children}</a>,
  code:({children,className})=>!className&&typeof children==='string'&&documentPath(children)?<DocumentLink path={children}>{children}</DocumentLink>:<code className={className}>{children}</code>,
  img:({alt})=><span className="ha-image-reference">{alt||'이미지 참조'}</span>
 }}>{displayEngineResponse(text)}</Markdown></div>;
});
