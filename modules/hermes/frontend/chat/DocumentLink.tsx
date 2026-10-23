import type {ReactNode} from 'react';
import {DocumentPreview,type PreviewDocument} from '@platform/ui/DocumentPreview';
import {request} from '@platform/data/api';
import {prefix} from '../types';

export {documentPath} from '@platform/ui/documentPaths';
export function DocumentLink({path,children}:{path:string;children?:ReactNode}){
 return <DocumentPreview path={path} load={p=>request<PreviewDocument>(prefix+'artifact',{path:p},'GET')}>{children}</DocumentPreview>;
}
