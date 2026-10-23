import {useCallback, useEffect, useState} from 'react';
import {ArrowRight, Box, Layers3, Link2, Plus, RefreshCw} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button, Empty, ErrorMessage, Skeleton, Status, Tabs} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {FoundationMap} from './FoundationMap';
import {ConnectionForm} from './ConnectionForm';
import {Connections} from './Connections';
import {Activity} from './Activity';
import {categoryName, stateLabel, type Category, type Connection, type Definition, type Overview} from './types';

const prefix = 'overlord/nazarick/';
const pages = [{id: 'overview', label: '기반 개요'}, {id: 'connections', label: '연결 대상'}, {id: 'activity', label: '작업 기록'}];
function currentPage() {return pages.find(page => location.hash === '#' + prefix + page.id)?.id ?? 'overview'}

export function Nazarick() {
  const [data, setData] = useState<Overview | null>(null), [error, setError] = useState('');
  const [loading, setLoading] = useState(false), [busy, setBusy] = useState(false), [page, setPage] = useState(currentPage);
  const [form, setForm] = useState<{item: Connection | null; category: Category; adapter?: Definition['adapter']} | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true);
    try {setData(await request<Overview>(prefix + 'overview', {}, 'GET')); setError('')}
    catch (failure) {setError(String(failure))} finally {setLoading(false)}
  }, []);
  useEffect(() => {void refresh(); const change = () => setPage(currentPage()); window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change)}, [refresh]);
  function navigate(id: string) {location.hash = prefix + id; setPage(id)}
  function add(category: Category = 'custom') {setForm({item: null, category})}
  async function mutate(operation: string, payload: unknown) {
    setBusy(true); setError('');
    try {await request(prefix + 'connections/' + operation, payload); await refresh()}
    catch (failure) {setError(String(failure)); throw failure} finally {setBusy(false)}
  }
  async function save(value: Definition) {await mutate('save', value)}
  if (!data) return <div className="space-y-5"><ErrorMessage message={error}/>{error ? <Button busy={loading} onClick={() => void refresh()}>다시 불러오기</Button> : <Skeleton/>}</div>;
  const targets = data.adapters.flatMap(adapter => adapter.targets);
  const counts = [
    {label: '사용할 수 있는 연결부', value: data.adapters.length, suffix: '종류', icon: Layers3},
    {label: '등록한 연결 대상', value: data.connections.length, suffix: '개', icon: Link2},
    {label: '등록을 확인한 대상', value: data.connections.filter(item => item.status === 'registered').length, suffix: '개', icon: Box},
  ];
  return <div className="space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-5"><div><p className="mb-2 font-mono text-xs tracking-widest text-brand-600">OVERLORD / FOUNDATION</p><h2 className="text-3xl font-semibold tracking-tight text-ink">나자릭</h2><p className="mt-2 text-sm leading-6 text-slate-500">본체를 세우고, 필요한 방향으로 확장합니다.</p></div><div className="flex gap-2"><Button busy={loading} disabled={busy} onClick={() => void refresh()} aria-label="기반 상태 새로고침"><RefreshCw size={15}/></Button><Button tone="primary" disabled={busy} onClick={() => add()}><Plus size={15}/>연결 대상 추가</Button></div></header>
    <ErrorMessage message={error}/>
    <div className="grid gap-4 sm:grid-cols-3">{counts.map(({label, value, suffix, icon: Icon}) => <div key={label} className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5"><div className="rounded-xl bg-brand-50 p-3 text-brand-600"><Icon size={20}/></div><div><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-2xl font-semibold tabular-nums text-ink">{value}<span className="ml-2 text-xs font-normal text-slate-400">{suffix}</span></p></div></div>)}</div>
    <Tabs items={pages} value={page} onChange={navigate}/>
    {page === 'overview' && <div className="space-y-6"><FoundationMap connections={data.connections} add={add}/><div className="grid gap-6 xl:grid-cols-2"><Panel title="지금 붙일 수 있는 기능" description="기존 플랫폼의 실제 등록 목록입니다. 등록 여부 확인은 엔진 가동이나 업무 실행을 의미하지 않습니다." actions={<Status>플랫폼 연결부</Status>}><p className="mb-4 text-sm leading-6 text-slate-500">기존 기능을 먼저 등록해 본체의 저장·확인·기록 흐름을 사용할 수 있습니다.</p><div className="flex flex-wrap gap-2">{targets.map(target => <span key={target.id} className="rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-600">{target.name}<span className="ml-2 text-slate-400">{target.available ? '등록됨' : '등록 오류'}</span></span>)}</div><div className="mt-5"><Button disabled={busy} onClick={() => setForm({item: null, category: 'execution', adapter: 'platform_module'})}>기능 등록하기<ArrowRight size={14}/></Button></div></Panel><Panel title="내 연결 대상" actions={<Button variant="ghost" onClick={() => navigate('connections')}>전체 보기<ArrowRight size={14}/></Button>}>{data.connections.length ? <div className="divide-y divide-slate-100">{data.connections.slice(0, 4).map(item => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="text-sm font-medium">{item.name}</p><p className="mt-1 text-xs text-slate-400">{categoryName(item.category)}</p></div><Status tone={item.status === 'registered' ? 'good' : item.status === 'failed' ? 'bad' : 'idle'}>{stateLabel[item.status] ?? item.status}</Status></div>)}</div> : <Empty title="아직 연결 대상을 정하지 않았습니다" detail="어느 서비스를 쓸지는 필요할 때 정해도 됩니다."/>}</Panel></div></div>}
    {page === 'connections' && <Connections items={data.connections} busy={busy} add={() => add()} edit={item => setForm({item, category: item.category})} inspect={item => void mutate('inspect', {id: item.id}).catch(() => {})} remove={item => mutate('remove', {id: item.id})}/>}
    {page === 'activity' && <Activity items={data.activity}/>}
    {form && <ConnectionForm key={form.item?.id ?? form.category} item={form.item} category={form.category} initialAdapter={form.adapter} adapters={data.adapters} close={() => setForm(null)} save={save}/>}
  </div>;
}
