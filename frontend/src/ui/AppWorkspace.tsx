import type {ReactNode} from 'react';
export function AppWorkspace({title,subtitle,actions,children}:{title:string;subtitle?:string;actions?:ReactNode;children:ReactNode}){
 return <main className="ui-app-workspace"><header className="ui-app-workspace-header"><div className="min-w-0"><h1 className="truncate text-base font-semibold">{title}</h1>{subtitle&&<p className="truncate text-xs text-slate-500">{subtitle}</p>}</div><div className="flex shrink-0 flex-wrap gap-2">{actions}</div></header>{children}</main>;
}
export function AppFrame({title,src}:{title:string;src:string}){
 return <iframe title={title} src={src} className="ui-app-workspace-frame" sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"/>;
}
