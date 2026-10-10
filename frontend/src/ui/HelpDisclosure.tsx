import type {ReactNode} from 'react';
import {Info} from 'lucide-react';

export function HelpDisclosure({title,children}:{title:string;children:ReactNode}){
 return <details onClick={e=>e.stopPropagation()} className="min-w-0 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
  <summary className="cursor-pointer rounded font-medium outline-none focus-visible:ring-2 focus-visible:ring-blue-400"><Info size={13} className="mr-1 inline-block align-text-bottom"/>{title}</summary>
  <div className="mt-3 space-y-2 break-words leading-6 text-slate-600">{children}</div>
 </details>;
}
