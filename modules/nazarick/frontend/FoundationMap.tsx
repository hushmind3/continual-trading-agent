import {ArrowUpRight, Box, CircleDot, CreditCard, Database, Fingerprint, Megaphone, Plus, Workflow} from 'lucide-react';
import {Button, Status} from '@platform/ui/Primitives';
import {categories, type Category, type Connection} from './types';

const icons = {execution: Workflow, data: Database, identity: Fingerprint, payment: CreditCard, distribution: Megaphone, custom: Plus};

export function FoundationMap({connections, add}: {connections: Connection[]; add: (category: Category) => void}) {
  function port(category: typeof categories[number]) {
    const Icon = icons[category.id], items = connections.filter(item => item.category === category.id);
    return <div key={category.id} className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-center justify-between gap-3"><Icon size={20} className="text-brand-600"/><span className="text-xs text-slate-400">{items.length ? `${items.length}개 대상` : '대상 미정'}</span></div>
      <h3 className="font-semibold text-slate-800">{category.name}</h3>
      <p className="mt-1 text-xs leading-5 text-slate-500">{category.detail}</p>
      <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-100 pt-3">
        <span className="truncate text-xs text-slate-500">{items[0]?.name ?? '필요할 때 연결하세요'}</span>
        <Button variant="ghost" onClick={() => add(category.id)} aria-label={category.name + ' 연결 대상 추가'}><ArrowUpRight size={15}/></Button>
      </div>
    </div>;
  }
  return <section aria-label="본체와 확장 구조" className="grid gap-4 lg:grid-cols-3">
    <div className="grid gap-4">{categories.slice(0, 3).map(port)}</div>
    <div className="order-first flex flex-col justify-center rounded-2xl bg-ink p-6 text-white sm:p-8 lg:order-none">
      <div className="mb-8 flex items-center justify-between gap-3"><span className="font-mono text-xs tracking-widest text-brand-200">CORE / 01</span><Status tone="good" inverted>본체 조회됨</Status></div>
      <Box size={44} strokeWidth={1.3} className="mb-6 text-brand-200"/>
      <h2 className="text-3xl font-semibold tracking-tight">나자릭</h2>
      <p className="mt-3 text-sm leading-7 text-brand-100">연결할 곳이 생기면,<br/>여기서 확장을 시작합니다.</p>
      <div className="my-7 h-px bg-brand-700"/>
      <div className="space-y-4 text-sm">{[
        ['등록', '대상과 역할을 같은 형식으로'],
        ['확인', '연결부가 확인한 범위까지'],
        ['기록', '변경과 결과를 본체에 보존'],
      ].map(([title, detail]) => <div key={title} className="flex gap-3"><CircleDot size={16} className="mt-1 shrink-0 text-brand-300"/><div><b className="font-medium">{title}</b><p className="mt-1 text-xs text-brand-200">{detail}</p></div></div>)}</div>
      <p className="mt-8 border-t border-brand-700 pt-5 text-xs leading-6 text-brand-200">외부 서비스와 사업 방향은 열어둔 상태입니다.</p>
    </div>
    <div className="grid gap-4">{categories.slice(3).map(port)}</div>
  </section>;
}
