import {useState} from 'react';
import {ExternalLink, KeyRound, Plus} from 'lucide-react';
import {Button, Empty, Input, Select, Status, Textarea} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {progress, type Progress, type Service} from './types';

export function Services({items, busy, vault, action}: {items: Service[]; busy: boolean; vault: boolean; action: (name: string, payload: unknown) => Promise<void>}) {
  const [importing, setImporting] = useState(false), [text, setText] = useState('');
  const [keyFor, setKeyFor] = useState(''), [secret, setSecret] = useState(''), [localError, setLocalError] = useState('');
  async function importItems() {
    setLocalError('');
    try {
      const entries = text.split('\n').map(line => line.trim()).filter(Boolean).map(line => {
        const match = line.match(/^(?:(.*?)\s+)?(https:\/\/\S+)$/);
        if (!match) throw new Error('각 줄에 업체명과 HTTPS 가입 주소를 입력하세요.');
        const url = new URL(match[2]), existing = items.find(item => new URL(item.url).hostname === url.hostname);
        return {id: existing?.id ?? url.hostname.replace(/[^a-zA-Z0-9_-]/g, '-'), name: match[1]?.trim() || url.hostname, url: url.href,
          login: existing?.login ?? 'google', status: existing?.status ?? 'pending', notes: existing?.notes ?? ''};
      });
      if (!entries.length || entries.length > 100) throw new Error('한 번에 1~100개 업체를 입력하세요.');
      await action('services/import', {items: entries}); setText(''); setImporting(false);
    } catch (failure) {setLocalError(String(failure))}
  }
  function update(item: Service, changes: Partial<Service>) {
    const {credential_saved: _key, updated_at: _date, ...value} = item;
    void action('services/save', {...value, ...changes}).catch(() => {});
  }
  return <div className="space-y-5">
    <Panel title="업체·가입 대기" actions={<Button disabled={busy} onClick={() => setImporting(!importing)}><Plus size={15}/>업체 일괄 추가</Button>}>
      <p className="mb-4 text-xs leading-5 text-slate-500">대기 {items.filter(item => item.status === 'pending').length} · 내 인증 필요 {items.filter(item => item.status === 'waiting_user').length} · 가입 기록 {items.filter(item => ['registered', 'key_ready'].includes(item.status)).length}. 진행 상태는 사용자·에이전트의 기록이며 실제 가입을 자동 검증한 결과가 아닙니다.</p>
      {importing && <div className="mb-5 space-y-3 rounded-xl border border-slate-200 p-4"><label className="block space-y-2 text-sm">업체명과 가입 주소를 한 줄에 하나씩<Textarea aria-label="가입할 업체 목록" rows={8} value={text} onChange={event => setText(event.target.value)} placeholder={'업체명 https://공식가입주소\n업체명 https://공식가입주소'}/></label><p className="text-xs text-slate-500">기존 업체의 진행 기록과 키는 유지합니다. 비밀번호·API 키를 입력하지 마세요.</p>{localError && <p role="alert" className="text-xs text-rose-600">{localError}</p>}<Button tone="primary" busy={busy} onClick={() => void importItems()}>대기 목록에 저장</Button></div>}
      {!items.length ? <Empty title="가입할 업체를 추가하세요" detail="34개도 한 번에 붙여넣을 수 있습니다. 공용 브라우저에서 순서대로 진행합니다."/> : <div className="space-y-4">{items.map(item => <article key={item.id} className="space-y-3 rounded-xl border border-slate-200 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold">{item.name}</h3><Status tone={item.status === 'waiting_user' ? 'warn' : item.status === 'failed' ? 'bad' : item.status === 'key_ready' ? 'good' : 'idle'}>{progress[item.status]}</Status></div>
        <p className="break-all text-xs text-slate-400">{item.url}</p>
        <div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={() => void action('browser/open', {target: item.id}).catch(() => {})}><ExternalLink size={14}/>공용 브라우저에서 열기</Button><Button disabled={busy || !vault} onClick={() => {setKeyFor(keyFor === item.id ? '' : item.id); setSecret('')}}><KeyRound size={14}/>{item.credential_saved ? '키 교체' : '키 보관'}</Button></div>
        <div className="grid gap-3 sm:grid-cols-2"><label className="space-y-1 text-xs text-slate-500">로그인 방식<Select aria-label={item.name + ' 로그인 방식'} disabled={busy} value={item.login} onChange={event => update(item, {login: event.target.value})}><option value="google">Google</option><option value="github">GitHub</option><option value="email">이메일</option><option value="other">기타</option></Select></label><label className="space-y-1 text-xs text-slate-500">진행 기록<Select aria-label={item.name + ' 진행 기록'} disabled={busy} value={item.status} onChange={event => update(item, {status: event.target.value as Progress})}>{Object.entries(progress).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</Select></label></div>
        {item.notes && <p className="whitespace-pre-wrap break-words text-xs text-slate-500">{item.notes}</p>}
        {Boolean(item.credential_saved) && <p className="text-xs text-brand-600">키체인에 키 보관 기록 있음</p>}
        {keyFor === item.id && <form className="space-y-2" onSubmit={event => {event.preventDefault(); void action('credential', {id: item.id, secret}).then(() => {setSecret(''); setKeyFor('')}).catch(() => {setSecret('')})}}><Input aria-label={item.name + ' API 키'} type="password" autoComplete="off" value={secret} onChange={event => setSecret(event.target.value)} placeholder="API 키 · 저장 후 다시 표시하지 않음" required maxLength={16384}/><div className="flex gap-2"><Button type="submit" tone="primary" busy={busy}>키체인에 저장</Button><Button disabled={busy} onClick={() => {setKeyFor(''); setSecret('')}}>취소</Button></div></form>}
      </article>)}</div>}
    </Panel>
  </div>;
}
