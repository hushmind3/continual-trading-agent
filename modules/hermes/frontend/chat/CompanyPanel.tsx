import type {RefObject} from 'react';
import {ExternalLink} from 'lucide-react';
import {Panel} from '@platform/ui/Panel';
import {PanelResizeHandle} from '@platform/ui/PanelResizeHandle';
import {CompanyApprovals,type Venture,type CompanyProgress} from './CompanyConversation';

export function CompanyPanel({panel,id,items,progress,pending,readOnly,decide}:{panel:RefObject<HTMLElement|null>;id:string;items:Venture[];progress?:CompanyProgress;pending:boolean;readOnly:boolean;decide:(id:string,approve:boolean)=>void}){
 return <aside id="hermes-company-panel" ref={panel} className="hermes-log ha-company-panel" aria-label="사업 관리"><PanelResizeHandle target={panel} storageKey="hermes.company.width" label="사업 관리 너비 조절"/><div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
  {items.length>0&&<Panel title="승인할 초안" collapsible={false}><CompanyApprovals items={items} pending={pending} readOnly={readOnly} decide={decide}/></Panel>}
  <Panel title="사업 진행" collapsible={false}><dl className="divide-y divide-slate-100 text-sm"><div className="flex justify-between gap-3 py-3"><dt>실행 승인 제품</dt><dd className="font-semibold">{progress?progress.published?(progress.free_trial?'무료 베타 운영 중':'운영 중'):progress.preview_url?'로컬 제품 준비됨':progress.approved?'로컬 제작 승인됨':'승인 대기':'확인 중'}</dd></div><div className="flex justify-between gap-3 py-3"><dt>고객 생성 요청</dt><dd className="font-semibold">{progress?.usage?.requests==null?'확인 중':progress.usage.requests.toLocaleString('ko-KR')+'건'}</dd></div><div className="flex justify-between gap-3 py-3"><dt>결제 매출</dt><dd className="font-semibold">{progress?progress.payment_connected?'집계 미확인':'연결 전':'확인 중'}</dd></div></dl><CompanyProduct id={id} progress={progress}/>{progress?.preview_url&&<p className="mt-2 text-xs text-slate-500">{progress.product_name} · 로컬 실행 결과입니다. 외부 공개·결제는 연결 전입니다.</p>}</Panel>
 </div></aside>;
}

/** Only API-confirmed local builds or published products have an actionable link. */
export function CompanyProduct({id,progress}:{id:string;progress?:CompanyProgress}){
 const path=progress?.preview_url||(progress?.published?progress.product_url:undefined);
 if(!path?.startsWith('/')||path.startsWith('//'))return null;
 return <a className="ha-company-product" href={'/assets/projects/'+id+path} target="_blank" rel="noopener noreferrer"><span><small>완성된 결과물</small><strong>{progress?.product_name||'프로젝트 결과물'}</strong></span><span>결과물 보기 <ExternalLink size={16}/></span></a>;
}
