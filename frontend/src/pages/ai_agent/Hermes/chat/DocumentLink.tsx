import type {ReactNode} from 'react';
import {DocumentPreview,type PreviewDocument} from '../../../../ui/DocumentPreview';
import {request} from '../../../../data/api';
import {prefix} from '../types';

export {documentPath} from '../../../../ui/documentPaths';
export function DocumentLink({path,children}:{path:string;children?:ReactNode}){
 return <DocumentPreview path={path} load={p=>request<PreviewDocument>(prefix+'artifact',{path:p},'GET')}>{children}</DocumentPreview>;
}
