import {Clock3} from 'lucide-react';
import {Empty, Status} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {stateLabel, timeLabel, type Activity as ActivityItem} from './types';

const actions: Record<string, string> = {created: '대상 등록', updated: '대상 수정', inspected: '등록 확인', removed: '정의 제거'};
export function Activity({items}: {items: ActivityItem[]}) {
  return <Panel title="작업 기록" actions={<span className="text-xs text-slate-400">최근 100건</span>}>
    {!items.length ? <Empty title="아직 실행 기록이 없습니다" detail="대상 등록·수정·확인 결과가 이곳에 쌓입니다."/> : <div className="divide-y divide-slate-100">{items.map(item => <article key={item.id} className="flex gap-4 py-5 first:pt-0 last:pb-0"><Clock3 size={17} className="mt-1 shrink-0 text-slate-400"/><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-3"><p className="break-words text-sm font-semibold">{item.name}<span className="ml-2 font-normal text-slate-400">{actions[item.action] ?? item.action}</span></p><Status tone={item.status === 'registered' ? 'good' : item.status === 'failed' ? 'bad' : 'idle'}>{stateLabel[item.status] ?? item.status}</Status></div><p className="mt-2 text-sm leading-6 text-slate-600">{item.detail.message}</p>{item.detail.scope && <p className="mt-1 text-xs leading-6 text-slate-400">{item.detail.scope}</p>}{item.detail.operations && <details className="mt-3 text-xs text-slate-500"><summary className="cursor-pointer">확인된 연결 규격 {item.detail.operations.length}개</summary><ul className="mt-2 space-y-1 break-all font-mono">{item.detail.operations.map(operation => <li key={operation}>{operation}</li>)}</ul></details>}<time className="mt-3 block text-xs text-slate-400" dateTime={item.created_at}>{timeLabel(item.created_at)}</time></div></article>)}</div>}
  </Panel>;
}
