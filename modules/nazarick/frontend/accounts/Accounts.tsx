import {useCallback, useEffect, useState} from 'react';
import {ExternalLink, Globe, KeyRound, Link2, RefreshCw, ShieldCheck} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button, ErrorMessage, Status} from '@platform/ui/Primitives';
import {SettingsSection, SettingsLoadState} from '@platform/ui/SettingsSection';
import type {SharedSettingsProps} from '@platform/shell/module_loader';
import {Services} from './Services';
import {Credentials} from './Credentials';
import {operation, type SharedState} from './types';

export function Accounts({page: tab, navigate: selectPage}: SharedSettingsProps) {
  const [data, setData] = useState<SharedState | null>(null);
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false), [refreshing, setRefreshing] = useState(false);
  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {setData(await request<SharedState>(operation + 'status', {}, 'GET')); setError('')}
    catch (failure) {setError(String(failure)); throw failure} finally {setRefreshing(false)}
  }, []);
  useEffect(() => {void refresh().catch(() => {})}, [refresh]);
  async function action(name: string, payload: unknown = {}) {
    setBusy(true); setError(''); setNotice('');
    try {await request(operation + name, payload); await refresh(); setNotice(name === 'agents/connect' ? '공용 연결 설정을 저장했습니다. 새 에이전트 연결·대화부터 사용합니다.' : name.startsWith('browser/') ? '전용 브라우저 창을 확인하세요.' : '저장했습니다.')}
    catch (failure) {setError(String(failure)); throw failure} finally {setBusy(false)}
  }
  function navigate(id: string) {selectPage(id); setNotice('')}
  const click = (name: string, payload: unknown = {}) => {void action(name, payload).catch(() => {})};
  const browserState = data?.browser.state === 'ready' ? '실행 중' : data?.browser.state === 'starting' ? '준비 중' : '꺼짐';
  return <div className="space-y-5"><div className="flex justify-end"><Button aria-label="공용 설정 새로고침" busy={refreshing} disabled={busy} onClick={() => void refresh().catch(() => {})}><RefreshCw size={15}/></Button></div>
    <ErrorMessage message={data ? error : ''}/>{notice && <p role="status" className="ui-settings-notice">{notice}</p>}
    {!data ? <SettingsLoadState error={error} retry={() => void refresh().catch(() => {})}/> : <div className="space-y-5">
      {tab === 'general' && <>
        <SettingsSection title="공용 설정" description="개별 에이전트 설정과 별도로, 함께 쓸 계정과 연결을 여기에서 관리합니다.">
          <div className="ui-settings-summary-row"><ShieldCheck size={23}/><div><p className="font-semibold">한 번 준비하고, 여러 에이전트가 함께 사용</p><p className="mt-1 text-sm leading-6 text-slate-500">로그인 계정·브라우저·API 키를 필요한 곳에서 재사용합니다.</p></div></div>
          <div className="ui-settings-overview-grid">{[
            {id: 'browser', title: '공용 브라우저', value: browserState},
            {id: 'accounts', title: '등록한 업체', value: data.services.length + '개'},
            {id: 'agents', title: '에이전트 연결', value: data.agents.configured ? '설정 저장됨' : '설정 전'},
            {id: 'keys', title: '키 보관 기록', value: data.services.filter(item => item.credential_saved).length + '개'},
          ].map(item => <Button key={item.id} variant="ghost" className="ui-settings-overview-item" onClick={() => navigate(item.id)}><span>{item.title}</span><strong>{item.value}</strong></Button>)}</div>
        </SettingsSection>
        <SettingsSection title="시작하기"><ol className="space-y-4 text-sm text-slate-600"><li><Button variant="ghost" onClick={() => navigate('accounts')}>1. Google·GitHub 로그인과 업체 등록<ExternalLink size={14}/></Button></li><li><Button variant="ghost" onClick={() => navigate('agents')}>2. 공용으로 사용할 에이전트 연결<Link2 size={14}/></Button></li><li><Button variant="ghost" onClick={() => navigate('keys')}>3. 발급받은 API 키 보관<KeyRound size={14}/></Button></li></ol></SettingsSection>
      </>}
      {tab === 'accounts' && <>
        <SettingsSection title="로그인 계정" description="전용 브라우저에서 직접 로그인하면 이후 가입 작업에 같은 계정을 사용합니다.">
          {([{id: 'google', name: 'Google', detail: 'Google로 계속하기를 지원하는 서비스'}, {id: 'github', name: 'GitHub', detail: 'GitHub 로그인을 지원하는 개발 도구·서비스'}]).map(item => <div key={item.id} className="ui-settings-account-row"><div><p className="font-semibold">{item.name}</p><p className="mt-1 text-xs text-slate-500">{item.detail}</p></div><Button disabled={busy} onClick={() => click('browser/open', {target: item.id})}>{item.name} 로그인<ExternalLink size={14}/></Button></div>)}
          <p className="text-xs text-slate-400">로그인 여부와 계정 선택은 열린 브라우저에서 확인합니다.</p>
        </SettingsSection>
        <Services items={data.services} busy={busy} action={action} manageKeys={() => navigate('keys')}/>
      </>}
      {tab === 'browser' && <>
        <SettingsSection title="공용 브라우저" actions={<Status tone={data.browser.state === 'ready' ? 'good' : 'idle'}>{browserState}</Status>}>
          <p className="text-sm leading-6 text-slate-500">설치된 Chrome·Edge를 전용 프로필로 실행합니다. 로그인 상태는 창을 닫아도 같은 프로필에 남습니다.</p>
          <div className="flex flex-wrap gap-2"><Button tone="primary" busy={busy} onClick={() => click('browser/start')}><Globe size={15}/>{data.browser.state === 'ready' ? '브라우저 연결 확인' : '공용 브라우저 열기'}</Button><Button onClick={() => navigate('accounts')}>로그인 계정 관리</Button></div>
          <p className="text-xs leading-5 text-slate-400">추가 인증·CAPTCHA가 나오면 직접 완료한 뒤 작업을 이어갑니다.</p>
        </SettingsSection>
        <SettingsSection title="연결 정보"><dl className="ui-settings-info-list"><div><dt>브라우저</dt><dd>{data.browser.browser || '실행 후 확인'}</dd></div><div><dt>상태</dt><dd>{browserState}</dd></div><div><dt>이 컴퓨터의 연결 주소</dt><dd>{data.browser.endpoint || '실행 후 표시'}</dd></div></dl></SettingsSection>
      </>}
      {tab === 'agents' && <SettingsSection title="연결된 에이전트" description="연결 설정을 저장한 상태이며 실제 로그인·작업 성공 여부와는 별도입니다.">
        {[
          {name: 'Codex', configured: data.agents.codex, detail: '공용 브라우저·계정 도구 · 다음 도구 연결부터 적용'},
          {name: 'Hermes', configured: Boolean(data.agents.hermes_profiles?.length), detail: `브라우저 도구·공용 계정 스킬 · ${data.agents.hermes_profiles?.length ?? 0}개 프로필 설정`},
          {name: 'OpenClaw', configured: data.agents.openclaw, detail: '공용 브라우저 프로필·공용 계정 스킬'},
        ].map(item => <div className="ui-settings-account-row" key={item.name}><div><p className="font-semibold">{item.name}</p><p className="mt-1 text-xs leading-5 text-slate-500">{item.detail}</p></div><Status tone={item.configured ? 'good' : 'idle'}>{item.configured ? '설정 저장됨' : '설정 전'}</Status></div>)}
        <div><Button disabled={busy} onClick={() => click('agents/connect')}><Link2 size={15}/>에이전트 공용 연결 설정</Button><p className="mt-3 text-xs leading-5 text-slate-400">실행 중인 작업을 강제로 재시작하지 않습니다. Hermes는 새 대화부터 공용 설정을 읽습니다.</p></div>
      </SettingsSection>}
      {tab === 'keys' && <Credentials items={data.services} busy={busy} available={data.vault.available} action={action} add={() => navigate('accounts')}/>}
      {tab === 'storage' && <>
        <SettingsSection title="저장 위치"><dl className="ui-settings-info-list"><div><dt>로그인·브라우저 프로필</dt><dd>{data.browser.profile}</dd></div><div><dt>업체·진행 기록</dt><dd>runtime/overlord/nazarick/accounts/accounts.sqlite3</dd></div><div><dt>API 키</dt><dd>{data.vault.available ? data.vault.name : '현재 운영체제에서 보관 미지원'}</dd></div></dl></SettingsSection>
        <SettingsSection title="자료 보관"><p className="text-sm leading-6 text-slate-500">로그인 상태·업체 기록·API 키는 GitHub에 올리지 않습니다. 연결 설정을 바꾸기 전의 원래 설정은 같은 공용 설정 런타임 안에 보관합니다.</p><p className="text-xs leading-5 text-slate-400">공용 설정 창을 닫아도 로그인 프로필과 저장한 업체 기록은 유지됩니다.</p></SettingsSection>
      </>}
    </div>}
  </div>;
}
