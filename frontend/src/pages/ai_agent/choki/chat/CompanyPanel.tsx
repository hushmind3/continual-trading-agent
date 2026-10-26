import type {RefObject} from 'react';
import {ExternalLink} from 'lucide-react';
import {Panel} from '@platform/ui/Panel';
import {PanelResizeHandle} from '@platform/ui/PanelResizeHandle';
import {CompanyApprovals,type Venture,type CompanyProgress} from './CompanyConversation';

export function CompanyPanel({panel,id,items,progress,pending,readOnly,decide}:{panel:RefObject<HTMLElement|null>;id:string;items:Venture[];progress?:CompanyProgress;pending:boolean;readOnly:boolean;decide:(id:string,approve:boolean)=>void}){
 return <aside id="hermes-company-panel" ref={panel} className="hermes-log ha-company-panel" aria-label="사업 관리"><PanelResizeHandle target={panel} storageKey="hermes.company.width" label="사업 관리 너비 조절"/><div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
  <Panel title="사업 초안" collapsible={false}><p className="mb-3 text-sm leading-relaxed text-copy">AI 팀이 작성한 사업 초안을 여기서 승인하거나 수정할 수 있습니다.</p>{items.length?<CompanyApprovals items={items} pending={pending} readOnly={readOnly} decide={decide}/>:<p className="text-sm text-slate-500">새 초안이 작성되면 여기에 표시됩니다.</p>}</Panel>
  <Panel title="사업 진행" collapsible={false}><dl className="divide-y divide-slate-100 text-sm"><div className="flex justify-between gap-3 py-3"><dt>진행 중인 프로젝트</dt><dd className="font-semibold">{progress?.approved==null?'확인 중':progress.approved.toLocaleString('ko-KR')+'개'}</dd></div><div className="flex justify-between gap-3 py-3"><dt>실행 가능한 제품</dt><dd className="font-semibold">{progress?.ready_products==null?'확인 중':progress.ready_products.toLocaleString('ko-KR')+'개'}</dd></div></dl><CompanyProduct id={id} progress={progress}/></Panel>
 </div></aside>;
}

/** Only API-confirmed local builds or published products have an actionable link. */
export function CompanyProduct({id,progress}:{id:string;progress?:CompanyProgress}){
 const path=progress?.preview_url||(progress?.published?progress.product_url:undefined);
 if(!path?.startsWith('/')||path.startsWith('//'))return null;
 return <a className="ha-company-product" href={'/assets/projects/'+id+path} target="_blank" rel="noopener noreferrer"><span><small>완성된 결과물</small><strong>{progress?.product_name||'프로젝트 결과물'}</strong></span><span>결과물 보기 <ExternalLink size={16}/></span></a>;
}
