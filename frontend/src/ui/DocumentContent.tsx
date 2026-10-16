import {useMemo} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type {PreviewDocument} from './DocumentPreview';

export function DocumentContent({document,source=false}:{document:PreviewDocument;source?:boolean}) {
  const html=useMemo(()=>'<!doctype html><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; font-src data:; form-action \'none\'; base-uri \'none\'">'+document.content,[document.content]);
  if(source)return <pre className="ui-document-source">{document.content}</pre>;
  if(document.format==='.html')return <iframe className="ui-document-html" title="HTML 문서 미리보기" sandbox="" referrerPolicy="no-referrer" srcDoc={html}/>;
  if(document.format==='.md')return <div className="ha-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{img:({alt})=><span>{alt||'이미지 참조'}</span>,a:({href,children})=><a href={href} target="_blank" rel="noreferrer">{children}</a>}}>{document.content}</Markdown></div>;
  return <pre className="ui-document-source">{document.content}</pre>;
}
