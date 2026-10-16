import type {ReactNode} from 'react';
import {DocumentPreview,type PreviewDocument} from '../../../../ui/DocumentPreview';
import {request} from '../../../../data/api';
import {prefix} from '../types';

export function documentPath(value:string){
 const path=value.trim();
 if(!/\.(md|txt|json|csv|log|py|tsx?|jsx?|yaml|yml|toml|html|css)$/i.test(path))return;
 if(/^[a-z][a-z0-9+.-]*:/i.test(path)&&!/^file:/i.test(path)&&!/^[a-z]:[\\/]/i.test(path))return;
 return path;
}
export function DocumentLink({path,children}:{path:string;children?:ReactNode}){
 return <DocumentPreview path={path} load={p=>request<PreviewDocument>(prefix+'artifact',{path:p},'GET')}>{children}</DocumentPreview>;
}
