import {Suspense,useEffect} from 'react';
import {MemoryRouter,Routes,Route,useLocation,useNavigate} from 'react-router';
import {Button} from '@platform/ui/Primitives';
import {BUILTIN_ROUTES_CORE,BUILTIN_NAV_REST} from '@hermes-official/App';
import {I18nProvider,useI18n} from '@hermes-official/i18n';
import {ThemeProvider} from '@hermes-official/themes';
import {useProfileScope} from '@hermes-official/contexts/useProfileScope';
import {ProfileProvider} from '@hermes-official/contexts/ProfileProvider';
import {ProfileSwitcher} from '@hermes-official/components/ProfileSwitcher';
import {SystemActionsProvider} from '@hermes-official/contexts/SystemActions';
import {PageHeaderProvider} from '@hermes-official/contexts/PageHeaderProvider';
import {PluginPage,usePlugins,exposePluginSDK} from '@hermes-official/plugins';
import {ResumeSession} from './ResumeSession';

const labels:Record<string,string>={'/sessions':'대화 기록','/files':'파일','/analytics':'사용량 분석','/models':'모델','/logs':'실행 로그','/cron':'예약 작업','/skills':'스킬','/plugins':'플러그인','/mcp':'도구 연결','/pairing':'연결 승인','/channels':'메신저 연결','/webhooks':'외부 알림 연결','/system':'시스템 관리','/profiles':'프로필','/profiles/new':'프로필 만들기','/config':'전체 설정','/env':'인증 정보','/docs':'사용 안내'};
exposePluginSDK();

function Pages({page}:{page?:string}){
 const navigate=useNavigate(),location=useLocation(),{setLocale}=useI18n();
 const {profile}=useProfileScope();
 const {manifests}=usePlugins(profile);
 useEffect(()=>{setLocale('ko')},[setLocale]);
 useEffect(()=>{if(page)navigate(page)},[page,navigate]);
 const tabs=manifests.filter(m=>!m.tab.hidden).map(m=>({path:m.tab.override??m.tab.path,label:m.name==='kanban'?'업무 보드':m.name==='hermes-achievements'?'활동 기록':m.label}));
 return <><div className="ha-official-controls"><ProfileSwitcher/>{(!page||location.pathname!==page)&&<nav className="hermes-tabs ha-official-tabs" aria-label="헤르메스 전체 기능">
 {BUILTIN_NAV_REST.map(item=><Button key={item.path} aria-pressed={location.pathname===item.path} onClick={()=>navigate(item.path)}>{labels[item.path]??'추가 기능'}</Button>)}
 {tabs.filter(tab=>!BUILTIN_ROUTES_CORE[tab.path]).map(tab=><Button key={tab.path} aria-pressed={location.pathname===tab.path} onClick={()=>navigate(tab.path)}>{tab.label}</Button>)}
 </nav>}</div><PageHeaderProvider pluginTabs={tabs}><Suspense fallback={<p role="status">기능을 불러오고 있습니다.</p>}><Routes>
 {Object.entries(BUILTIN_ROUTES_CORE).map(([path,Component])=><Route key={path} path={path} element={<Component/>}/>)}
 <Route path="/chat" element={<ResumeSession/>}/>
 {manifests.filter(m=>!m.tab.hidden&&!BUILTIN_ROUTES_CORE[m.tab.path]).map(m=><Route key={m.name} path={m.tab.path+'/*'} element={<PluginPage name={m.name}/>}/>)}
 </Routes></Suspense></PageHeaderProvider></>;
}

export function OfficialWorkspace({page}:{page?:string}){
 return <div className="hermes-official"><MemoryRouter initialEntries={[page??'/config']}><I18nProvider><ThemeProvider><SystemActionsProvider><ProfileProvider><Pages page={page}/></ProfileProvider></SystemActionsProvider></ThemeProvider></I18nProvider></MemoryRouter></div>;
}
