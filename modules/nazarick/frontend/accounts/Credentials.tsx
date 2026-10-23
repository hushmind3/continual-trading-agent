import {useState} from 'react';
import {KeyRound, ShieldCheck} from 'lucide-react';
import {Button, Empty, Input, Select, Status} from '@platform/ui/Primitives';
import {SettingsSection} from '@platform/ui/SettingsSection';
import type {Service} from './types';

export function Credentials({items, busy, available, action, add}: {
  items: Service[]; busy: boolean; available: boolean; action: (name: string, payload: unknown) => Promise<void>; add: () => void;
}) {
  const [selected, setSelected] = useState(items[0]?.id ?? ''), [secret, setSecret] = useState('');
  const current = items.find(item => item.id === selected);
  return <div className="space-y-5">
    <SettingsSection title="API 키 보관함" description="업체별 키를 보관하고 필요한 실행에서 함께 사용합니다." actions={<Status tone={available ? 'good' : 'warn'}>{available ? 'macOS 키체인 사용' : '이 운영체제 미지원'}</Status>}>
      <div className="ui-settings-summary-row"><KeyRound size={20}/><div><p className="font-medium">{items.filter(item => item.credential_saved).length}개 업체의 키 보관 기록</p><p className="mt-1 text-xs text-slate-500">등록한 업체 {items.length}개 · 저장한 키는 화면에 다시 표시하지 않습니다.</p></div></div>
      {!items.length ? <Empty title="키를 보관할 업체가 없습니다" detail="계정·서비스에서 업체를 먼저 등록하세요." action={<Button onClick={add}>업체 등록하기</Button>}/> : <form className="space-y-4" onSubmit={event => {event.preventDefault(); void action('credential', {id: selected, secret}).then(() => setSecret('')).catch(() => setSecret(''))}}>
        <label className="block space-y-2 text-sm">업체 선택<Select aria-label="API 키 업체" disabled={busy} value={selected} onChange={event => {setSelected(event.target.value); setSecret('')}}>{items.map(item => <option value={item.id} key={item.id}>{item.name}{item.credential_saved ? ' · 보관 기록 있음' : ''}</option>)}</Select></label>
        <label className="block space-y-2 text-sm">{current?.credential_saved ? '교체할 API 키' : '보관할 API 키'}<Input aria-label="보관할 API 키" type="password" autoComplete="off" value={secret} disabled={busy || !available} onChange={event => setSecret(event.target.value)} required maxLength={16384} placeholder="키 입력 · 저장 후 입력값을 지웁니다"/></label>
        <Button type="submit" tone="primary" busy={busy} disabled={!available || !current}><ShieldCheck size={15}/>키체인에 저장</Button>
      </form>}
    </SettingsSection>
    <SettingsSection title="에이전트의 키 사용"><p className="text-sm leading-6 text-slate-500">키는 명령줄이나 진행 메모에 복사하지 않고, 필요한 프로그램을 실행할 때 환경변수로 전달합니다. 계정 로그인과 API 키 발급은 별도 단계입니다.</p></SettingsSection>
  </div>;
}
