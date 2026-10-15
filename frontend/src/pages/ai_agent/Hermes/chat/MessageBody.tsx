import {Children,isValidElement,memo,useState,type ReactNode} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {Check,Copy,TriangleAlert} from 'lucide-react';

export function CopyButton({text,label='복사'}:{text:string;label?:string}){
 const [state,setState]=useState<'idle'|'copied'|'error'>('idle');
 return <button type="button" className="ha-copy" title={label} aria-label={state==='copied'?'복사됨':label} onClick={()=>{void navigator.clipboard.writeText(text).then(()=>{setState('copied');setTimeout(()=>setState('idle'),1800)}).catch(()=>setState('error'))}}>{state==='copied'?<Check size={14}/>:state==='error'?<TriangleAlert size={14}/>:<Copy size={14}/>}<span>{state==='copied'?'복사됨':state==='error'?'복사 실패':label}</span></button>;
}
function CodeBlock({children}:{children?:ReactNode}){
 const child=Children.toArray(children)[0];
 const props=isValidElement<{children?:ReactNode;className?:string}>(child)?child.props:undefined;
 const code=String(props?.children??'').replace(/\n$/,'');
 const language=props?.className?.replace('language-','')??'코드';
 return <figure className="ha-code-block"><figcaption><span>{language}</span><CopyButton text={code} label="코드 복사"/></figcaption><pre>{children}</pre></figure>;
}
export const MessageBody=memo(function MessageBody({text,user=false}:{text:string;user?:boolean}){
 if(user)return <div className="ha-user-text">{text}</div>;
 return <div className="ha-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{
  pre:({children})=><CodeBlock>{children}</CodeBlock>,
  table:({children})=><div className="ha-table-scroll"><table>{children}</table></div>,
  a:({children,href})=><a href={href} target="_blank" rel="noreferrer">{children}</a>,
  img:({alt})=><span className="ha-image-reference">{alt||'이미지 참조'}</span>
 }}>{text}</Markdown></div>;
});
