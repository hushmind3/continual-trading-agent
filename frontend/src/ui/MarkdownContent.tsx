import {memo} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
/** Shared, script-free Markdown for conversations and app work results. */
export const MarkdownContent=memo(function MarkdownContent({text}:{text:string}){
 return <div className="ha-markdown break-words"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{img:({alt})=><span>{alt||'이미지 참조'}</span>,table:({children})=><div className="overflow-x-auto"><table>{children}</table></div>,a:({href,children})=><a href={href} target="_blank" rel="noreferrer">{children}</a>}}>{text}</Markdown></div>;
});
