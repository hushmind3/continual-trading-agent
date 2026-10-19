import type {RefObject} from 'react';
import {X} from 'lucide-react';
import {Button,IconButton} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {PanelResizeHandle} from '@platform/ui/PanelResizeHandle';
import {CompanyApprovals,type Venture,type CompanyProgress} from './CompanyConversation';

export function CompanyPanel({panel,id,items,progress,pending,readOnly,decide,onClose}:{panel:RefObject<HTMLElement|null>;id:string;items:Venture[];progress?:CompanyProgress;pending:boolean;readOnly:boolean;decide:(id:string,approve:boolean)=>void;onClose:()=>void}){
 const product=progress?.product_url,href=product&&product.startsWith('/')&&!product.startsWith('//')?'/assets/projects/'+id+product:undefined;
 return <aside ref={panel} className="hermes-log" aria-label="사업 관리"><PanelResizeHandle target={panel} storageKey="hermes.company.width" label="사업 관리 너비 조절"/><header><h3>사업 관리</h3><IconButton aria-label="사업 관리 닫기" onClick={onClose}><X size={18}/></IconButton></header><div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
  <Panel title="사업 초안" collapsible={false}>{items.length?<CompanyApprovals items={items} pending={pending} readOnly={readOnly} decide={decide}/>:<p className="text-sm leading-relaxed text-slate-500">CEO가 제안한 새 사업안을 여기서 승인하거나 수정할 수 있습니다.</p>}</Panel>
  <Panel title="사업 진행" collapsible={false}><dl className="divide-y divide-slate-100 text-sm"><div className="flex justify-between gap-3 py-3"><dt>실행 승인 제품</dt><dd className="font-semibold">{progress?progress.published?(progress.free_trial?'무료 베타 운영 중':'운영 중'):'승인 대기':'확인 중'}</dd></div><div className="flex justify-between gap-3 py-3"><dt>고객 생성 요청</dt><dd className="font-semibold">{progress?.usage?.requests==null?'확인 중':progress.usage.requests.toLocaleString('ko-KR')+'건'}</dd></div><div className="flex justify-between gap-3 py-3"><dt>결제 매출</dt><dd className="font-semibold">{progress?progress.payment_connected?'집계 미확인':'연결 전':'확인 중'}</dd></div></dl>{href?<a className="ui-link mt-4 block text-sm" href={href} target="_blank" rel="noopener noreferrer">고객용 독립 제품 보기 ↗</a>:<Button className="mt-4 w-full" disabled>고객용 제품 공개 전</Button>}</Panel>
 </div></aside>;
}
