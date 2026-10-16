import {Settings2, Plug, BookOpen, FileText, MessageSquare} from 'lucide-react';

export const hermesRoute = 'ai_agent/Hermes';
export const agentSettingsSections = [
  {id:'prompt', name:'시스템 프롬프트', description:'역할·작업 방식·응답 규칙', icon:FileText},
  {id:'models', name:'모델', description:'로컬 모델·서버·작업 도구', icon:Settings2},
  {id:'mcp', name:'MCP', description:'서버 설치와 연결 관리', icon:Plug},
  {id:'skills', name:'스킬', description:'작업 지침과 사용 설정', icon:BookOpen},
];
export const agentPages = [{id:'chat',name:'헤르메스 대화',icon:MessageSquare},...['models','mcp','skills','prompt'].map(id=>agentSettingsSections.find(section=>section.id===id)!)];
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
