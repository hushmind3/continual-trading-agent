import {Settings2, Plug, BookOpen, FileText, MessageSquare, FolderCog} from 'lucide-react';

export const hermesRoute = 'ai_agent/Hermes';
export const agentSettingsSections = [
  {id:'prompt', name:'시스템 프롬프트', description:'역할·작업 방식·응답 규칙', icon:FileText},
  {id:'agent-prompts', name:'개별 프롬프트', description:'총괄·직원별 전문성·말투·판단 기준', icon:FileText},
  {id:'models', name:'모델', description:'로컬 모델 선택과 서버 연결', icon:Settings2},
  {id:'workspace', name:'작업 환경', description:'작업 폴더·사용 도구·실행 한도', icon:FolderCog},
  {id:'mcp', name:'도구 연결', description:'MCP 서버 설치와 연결 관리', icon:Plug},
  {id:'skills', name:'스킬', description:'작업 지침과 사용 설정', icon:BookOpen},
  {id:'official', name:'전체 기능', description:'기억·프로필·플러그인·예약·메신저 등 공식 기능', icon:Settings2},
];
export const agentPages = [{id:'chat',name:'대화',icon:MessageSquare},...['models','workspace','mcp','skills','prompt','agent-prompts','official'].map(id=>agentSettingsSections.find(section=>section.id===id)!)];
export const agentHref = (id:string) => '#'+hermesRoute+(id==='chat'?'':'/'+id);
export function agentLocation() {
  const query = new URLSearchParams(location.hash.split('?')[1] || '');
  const part=location.hash.replace(/^#/, '').split('?')[0].slice(hermesRoute.length+1);
  const requested = part || query.get('section') || sessionStorage.getItem('hermes.settings.tab') || 'models';
  return {view: part || query.get('view') === 'settings' ? 'settings' : 'chat',
    section: agentSettingsSections.some(section => section.id === requested) ? requested : 'models'};
}
export function navigateAgent(view: 'chat'|'settings', section?: string) {
  location.hash = agentHref(view==='chat'?'chat':section||agentLocation().section);
}

export function openOfficial(path:string){
 sessionStorage.setItem('hermes:official:location',path);
 window.dispatchEvent(new CustomEvent('hermes:official-navigate',{detail:path}));
 navigateAgent('settings','official');
}

export const officialPageLabels:Record<string,string>={'/sessions':'대화 기록','/files':'파일','/analytics':'사용량 분석','/models':'모델','/logs':'실행 로그','/cron':'예약 작업','/skills':'스킬','/plugins':'플러그인','/mcp':'도구 연결','/pairing':'연결 승인','/channels':'봇·메신저 연결','/webhooks':'외부 알림 연결','/system':'시스템 관리','/profiles':'프로필','/profiles/new':'프로필 만들기','/config':'전체 설정','/env':'인증 정보','/docs':'사용 안내'};
