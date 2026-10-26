import {officialPageLabels as labels} from '../../agent_navigation';
import {Suspense,useEffect,useRef,useState} from 'react';
import {MemoryRouter,Routes,Route,useLocation,useNavigate} from '@hermes-official/platform-router';
import {Button} from '@platform/ui/Primitives';
import {ChevronLeft,ChevronRight} from 'lucide-react';
import {BUILTIN_ROUTES_CORE,BUILTIN_NAV_REST} from '@hermes-official/App';
import {I18nProvider,useI18n} from '@hermes-official/i18n';
import {ThemeProvider} from '@hermes-official/themes';
import {useProfileScope} from '@hermes-official/contexts/useProfileScope';
import {ProfileProvider} from '@hermes-official/contexts/ProfileProvider';
import {ProfileSwitcher} from '@hermes-official/components/ProfileSwitcher';
import {SystemActionsProvider} from '@hermes-official/contexts/SystemActions';
import {PageHeaderProvider} from '@hermes-official/contexts/PageHeaderProvider';
import {PluginPage,usePlugins,exposePluginSDK} from '@hermes-official/plugins';
import {NativeCommands,ResumeSession} from './ResumeSession';


exposePluginSDK();
const locationKey='hermes:official:location';
function initialLocation(page?:string){if(page)return page;try{const saved=sessionStorage.getItem(locationKey);return saved?.startsWith('/')&&!saved.startsWith('//')?saved:'/config'}catch{return '/config'}}

function Pages({page}:{page?:string}){
 const navigate=useNavigate(),location=useLocation(),{setLocale}=useI18n();
 const {profile}=useProfileScope();
 const {manifests}=usePlugins(profile);
 const chatQuery=new URLSearchParams(location.search);
 const commandActive=location.pathname==='/chat'&&(chatQuery.get('terminal')==='1'||Boolean(chatQuery.get('profile')&&chatQuery.get('profile')!=='default'))&&!manifests.some(m=>m.tab.override==='/chat');
 const [commandVisited,setCommandVisited]=useState(commandActive);
 useEffect(()=>{if(commandActive)setCommandVisited(true)},[commandActive]);
 const requestedPage=useRef(page);
 useEffect(()=>{const open=(event:Event)=>navigate((event as CustomEvent<string>).detail);window.addEventListener('hermes:official-navigate',open);return()=>window.removeEventListener('hermes:official-navigate',open)},[navigate]);
 useEffect(()=>{setLocale('ko')},[setLocale]);
 useEffect(()=>{if(!page){try{sessionStorage.setItem(locationKey,location.pathname+location.search)}catch{/* Storage is optional. */}}},[page,location.pathname,location.search]);
 useEffect(()=>{if(requestedPage.current!==page){requestedPage.current=page;if(page)navigate(page)}},[page,navigate]);
 const tabs=manifests.filter(m=>!m.tab.hidden).map(m=>({path:m.tab.override??m.tab.path,label:m.name==='kanban'?'업무 보드':m.name==='hermes-achievements'?'활동 기록':m.label}));
 return <><div className="ha-official-controls"><div className="ha-official-toolbar"><div className="ha-official-history"><Button aria-label="이전 기능" title="이전 기능" onClick={()=>navigate(-1)}><ChevronLeft/></Button><Button aria-label="다음 기능" title="다음 기능" onClick={()=>navigate(1)}><ChevronRight/></Button></div><ProfileSwitcher/></div>{(!page||location.pathname!==page)&&<nav className="hermes-tabs ha-official-tabs" aria-label="헤르메스 전체 기능">
 {BUILTIN_NAV_REST.map(item=><Button key={item.path} aria-pressed={location.pathname===item.path} onClick={()=>navigate(item.path)}>{labels[item.path]??'추가 기능'}</Button>)}
 <Button aria-pressed={location.pathname==='/chat'} onClick={()=>navigate('/chat?terminal=1'+(profile?'&profile='+encodeURIComponent(profile):''))}>명령 실행</Button>
 {tabs.filter(tab=>!BUILTIN_ROUTES_CORE[tab.path]).map(tab=><Button key={tab.path} aria-pressed={location.pathname===tab.path} onClick={()=>navigate(tab.path)}>{tab.label}</Button>)}
 </nav>}</div><PageHeaderProvider pluginTabs={tabs}>{(commandVisited||commandActive)&&<div className={commandActive?'ha-official-command-host':'hidden'}><NativeCommands active={commandActive}/></div>}<Suspense fallback={<p role="status">기능을 불러오고 있습니다.</p>}><Routes key={profile}>
 {Object.entries(BUILTIN_ROUTES_CORE).map(([path,Component])=>{const override=manifests.find(m=>m.tab.override===path);return <Route key={path} path={path} element={override?<PluginPage name={override.name}/>:<Component/>}/>})}
 <Route path="/chat" element={manifests.some(m=>m.tab.override==='/chat')?<PluginPage name={manifests.find(m=>m.tab.override==='/chat')!.name}/>:<ResumeSession/>}/>
 {manifests.filter(m=>!m.tab.hidden&&!BUILTIN_ROUTES_CORE[m.tab.path]).map(m=><Route key={m.name} path={m.tab.path+'/*'} element={<PluginPage name={m.name}/>}/>)}
 <Route path="*" element={<div className="ha-official-empty"><h2>기능을 찾을 수 없습니다</h2><p>선택한 기능이 이동했거나 해당 프로필의 플러그인이 비활성화됐습니다.</p><Button onClick={()=>navigate('/config')}>설정으로 이동</Button></div>}/>
 </Routes></Suspense></PageHeaderProvider></>;
}

export function OfficialWorkspace({page}:{page?:string}){
 return <div className="hermes-official"><MemoryRouter initialEntries={[initialLocation(page)]}><I18nProvider><ThemeProvider><SystemActionsProvider><ProfileProvider><Pages page={page}/></ProfileProvider></SystemActionsProvider></ThemeProvider></I18nProvider></MemoryRouter></div>;
}
