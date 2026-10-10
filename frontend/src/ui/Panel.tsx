import type {ReactNode} from 'react';
export function Panel({title,description,actions,children,className=''}:{title:string;description?:string;actions?:ReactNode;children:ReactNode;className?:string}) {
  return <section className={'min-w-0 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200/60 sm:p-6 '+className}>
    <header className="mb-5 flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-base font-bold">{title}</h2>{description&&<p className="mt-1 text-xs leading-5 text-slate-400">{description}</p>}</div>{actions}</header>{children}
  </section>;
}
export function KeyValues({items}:{items:[string,ReactNode][]}) {
  return <dl className="grid gap-x-6 sm:grid-cols-2">{items.map(([key,value])=><div className="min-w-0 border-b border-slate-100 py-3" key={key}><dt className="text-xs text-slate-400">{key}</dt><dd className="mt-1 break-words text-sm font-medium">{value??'미측정'}</dd></div>)}</dl>;
}
