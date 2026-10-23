import {useCallback, useEffect, useState} from 'react';
import {ExternalLink, Globe, Link2, RefreshCw, ShieldCheck} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button, ErrorMessage, Skeleton, Status, Tabs} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {Services} from './Services';
import {operation, type SharedState} from './types';

export function Accounts() {
  const [data, setData] = useState<SharedState | null>(null), [tab, setTab] = useState('browser');
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {setData(await request<SharedState>(operation + 'status', {}, 'GET'))}, []);
  useEffect(() => {void refresh().catch(failure => setError(String(failure)))}, [refresh]);
  async function action(name: string, payload: unknown = {}) {
    setBusy(true); setError(''); setNotice('');
    try {await request(operation + name, payload); await refresh(); setNotice(name === 'agents/connect' ? '공용 연결 설정을 저장했습니다. 새 에이전트 연결·대화부터 사용합니다.' : name === 'browser/start' || name === 'browser/open' ? '전용 브라우저 창을 확인하세요.' : '저장했습니다.')}
    catch (failure) {setError(String(failure)); throw failure} finally {setBusy(false)}
  }
  const click = (name: string, payload: unknown = {}) => {void action(name, payload).catch(() => {})};
  return <div className="space-y-5">
    <div className="flex items-start justify-between gap-3"><p className="text-sm leading-6 text-slate-500">여러 AI가 함께 사용할 로그인 브라우저와 업체 계정을 관리합니다.</p><Button aria-label="공용 설정 새로고침" disabled={busy} onClick={() => void refresh().catch(failure => setError(String(failure)))}><RefreshCw size={15}/></Button></div>
    <ErrorMessage message={error}/>{notice && <p role="status" className="text-sm text-brand-600">{notice}</p>}
    <Tabs items={[{id: 'browser', label: '공용 브라우저'}, {id: 'services', label: `업체·가입 대기${data ? ' ' + data.services.length : ''}`}]} value={tab} onChange={setTab}/>
    {!data ? <Skeleton/> : tab === 'browser' ? <div className="space-y-5">
      <Panel title="로그인 전용 브라우저" actions={<Status tone={data.browser.state === 'ready' ? 'good' : 'idle'}>{data.browser.state === 'ready' ? '실행 중' : data.browser.state === 'starting' ? '준비 중' : '꺼짐'}</Status>}>
        <p className="mb-4 text-sm leading-6 text-slate-500">처음에 Google·GitHub에 로그인해 두면, AI가 같은 브라우저에서 업체 가입과 설정을 이어갑니다. 로그인 상태는 창을 닫아도 전용 프로필에 남습니다.</p>
        <div className="flex flex-wrap gap-2"><Button tone="primary" busy={busy} onClick={() => click('browser/start')}><Globe size={15}/>{data.browser.state === 'ready' ? '브라우저 연결 확인' : '공용 브라우저 열기'}</Button><Button disabled={busy} onClick={() => click('browser/open', {target: 'google'})}>Google 로그인<ExternalLink size={14}/></Button><Button disabled={busy} onClick={() => click('browser/open', {target: 'github'})}>GitHub 로그인<ExternalLink size={14}/></Button></div>
        <p className="mt-4 text-xs leading-5 text-slate-400">로그인 여부는 열린 브라우저에서 확인합니다. 사이트의 추가 인증·CAPTCHA가 나오면 직접 완료한 뒤 작업을 이어가면 됩니다.</p>
      </Panel>
      <Panel title="에이전트 공용 연결">
        <p className="mb-4 text-sm leading-6 text-slate-500">Codex는 공용 브라우저·계정 MCP, Hermes는 기존 브라우저 도구, OpenClaw는 전용 연결 프로필을 사용합니다.</p>
        <Button disabled={busy} onClick={() => click('agents/connect')}><Link2 size={15}/>에이전트 공용 연결 설정</Button>
        <p className="mt-3 text-xs leading-5 text-slate-500">{data.agents.message}</p>
        {data.agents.configured && <p className="mt-2 text-xs leading-5 text-slate-400">Codex 설정 {data.agents.codex ? '저장됨' : '없음'} · Hermes {data.agents.hermes_profiles?.length ?? 0}개 프로필 · OpenClaw {data.agents.openclaw ? '저장됨' : '미설치'}. 실제 도구 연결·로그인 확인과는 별도입니다.</p>}
      </Panel>
      <Panel title="공용 키 보관"><p className="flex items-center gap-2 text-sm"><ShieldCheck size={16}/>{data.vault.available ? 'API 키는 macOS 키체인에 저장합니다.' : '이 운영체제의 공용 키 저장은 아직 지원하지 않습니다.'}</p><p className="mt-2 text-xs leading-5 text-slate-500">업체 탭에서 키를 보관할 수 있습니다. 저장한 키는 화면에 다시 표시하지 않으며 필요한 실행에 환경변수로 전달합니다.</p></Panel>
      <details className="text-xs text-slate-500"><summary className="cursor-pointer">연결·저장 위치</summary><dl className="mt-3 space-y-3 break-all"><div><dt>브라우저 프로필</dt><dd className="mt-1">{data.browser.profile}</dd></div><div><dt>이 컴퓨터의 공용 연결 주소</dt><dd className="mt-1">{data.browser.endpoint || '브라우저 실행 후 표시'}</dd></div></dl></details>
    </div> : <Services items={data.services} busy={busy} vault={data.vault.available} action={action}/>}
  </div>;
}
