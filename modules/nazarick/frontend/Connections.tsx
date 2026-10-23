import {useState} from 'react';
import {ArrowUpRight, Pencil, Plus, Trash2} from 'lucide-react';
import {Button, Empty, Status} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {categoryName, stateLabel, timeLabel, type Connection} from './types';

export function Connections({items, busy, add, edit, inspect, remove}: {
  items: Connection[]; busy: boolean; add: () => void; edit: (item: Connection) => void;
  inspect: (item: Connection) => void; remove: (item: Connection) => Promise<void>;
}) {
  const [removing, setRemoving] = useState<string | null>(null);
  return <Panel title="연결 대상" actions={<Button tone="primary" onClick={add}><Plus size={15}/>대상 추가</Button>}>
    {!items.length ? <Empty title="첫 연결 대상을 등록하세요" detail="외부 서비스는 예정 대상으로, 기존 플랫폼 기능은 등록을 확인할 대상으로 추가할 수 있습니다." action={<Button onClick={add}>연결 대상 추가</Button>}/> : <div className="space-y-3">{items.map(item => <article key={item.id} className="rounded-xl border border-slate-200 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-4"><div className="min-w-0"><div className="mb-2 flex flex-wrap items-center gap-3"><h3 className="break-words font-semibold">{item.name}</h3><Status tone={item.status === 'registered' ? 'good' : item.status === 'failed' ? 'bad' : 'idle'}>{stateLabel[item.status] ?? item.status}</Status></div><p className="text-xs text-slate-500">{categoryName(item.category)} · {item.adapter === 'planned' ? '외부 연결부 준비 전' : '플랫폼 기능 / ' + item.target}</p>{item.notes && <p className="mt-3 whitespace-pre-wrap break-words text-sm text-slate-600">{item.notes}</p>}</div>
      <div className="flex flex-wrap gap-2"><Button disabled={busy || item.adapter === 'planned'} onClick={() => inspect(item)}><ArrowUpRight size={14}/>등록 확인</Button><Button disabled={busy} onClick={() => edit(item)} aria-label={item.name + ' 수정'}><Pencil size={14}/></Button><Button disabled={busy} onClick={() => setRemoving(item.id)} aria-label={item.name + ' 연결 정의 제거'}><Trash2 size={14}/></Button></div></div>
      {item.checked_at && <p className="mt-4 text-xs text-slate-400">마지막 등록 확인 {timeLabel(item.checked_at)} · 실제 업무 실행 상태와는 별도입니다.</p>}
      {removing === item.id && <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4"><span className="text-xs text-slate-500">연결 정의만 제거하고 대상 기능은 유지합니다.</span><Button disabled={busy} onClick={() => setRemoving(null)}>취소</Button><Button tone="danger" disabled={busy} onClick={() => void remove(item).then(() => setRemoving(null)).catch(() => {})}>정의 제거</Button></div>}
    </article>)}</div>}
  </Panel>;
}
