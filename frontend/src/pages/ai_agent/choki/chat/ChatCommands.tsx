import {useEffect,useState,type KeyboardEvent} from 'react';
import {Button} from '@platform/ui/Primitives';
import {Plus,Cpu,Brain,Target,Repeat2,Activity,Plug,BookOpen,Terminal,Settings,MessageSquare,LogOut,ChevronRight,type LucideIcon} from 'lucide-react';
import {commandCatalog,type CommandCatalog} from './nativeCommands';

// Translations only: the installed Choki registry owns availability, aliases and arguments.
const names:Record<string,string>={new:'새 대화',clear:'화면 비우고 새 대화',redraw:'화면 다시 그리기',history:'대화 기록',save:'대화 내보내기',retry:'다시 시도',prompt:'프롬프트 작성',undo:'이전 대화로 되돌리기',title:'대화 이름',handoff:'메신저로 인계',branch:'대화 분기',worktree:'작업 사본',compress:'문맥 압축',rollback:'파일 변경 복원',snapshot:'상태 백업·복원',export:'프로필 내보내기',import:'프로필 가져오기',stop:'실행 중지',bg:'백그라운드 작업',btw:'곁가지 질문',agents:'에이전트',journey:'진행 기록',queue:'대기열',steer:'추가 지시',goal:'목표',heartbeat:'주기 점검',refine:'요청 다듬기',review:'검토',loop:'반복 실행',plan:'계획 모드',moa:'여러 모델 협업',subgoal:'하위 목표',status:'상태',egress:'외부 연결 정책',context:'문맥 사용량',whoami:'현재 연결 정보',profile:'프로필',resume:'대화 이어가기',sessions:'대화 목록',config:'설정',model:'모델','codex-runtime':'코덱스 실행 방식',personality:'성격·말투',statusbar:'상태 표시줄',battery:'배터리',timestamps:'시간 표시',diff:'변경 내용',verbose:'자세한 출력',focus:'집중 모드',footer:'하단 정보',yolo:'자동 승인',approvals:'승인 설정',reasoning:'추론 수준',fast:'빠른 처리',skin:'화면 테마',indicator:'진행 표시',voice:'음성',wake:'음성 호출',busy:'작업 중 처리 방식',autoprune:'기록 자동 정리',tools:'도구',toolsets:'도구 묶음',skills:'스킬',memory:'메모리',bundles:'스킬 묶음',pet:'동반자',hatch:'동반자 만들기',learn:'경험 학습',init:'작업 지침 초기화',cron:'예약 작업',suggestions:'제안',blueprint:'실행 초안',curator:'스킬 정리',kanban:'업무 보드',reload:'설정 다시 읽기','reload-mcp':'도구 연결 다시 읽기','reload-skills':'스킬 다시 읽기',browser:'브라우저',plugins:'플러그인',help:'도움말',palette:'명령 찾기',usage:'사용량',subscription:'이용권',login:'로그인',topup:'크레딧 충전',insights:'사용 분석',platforms:'메신저 연결',copy:'복사',paste:'붙여넣기',image:'이미지',update:'업데이트',version:'버전',debug:'진단',quit:'종료',commands:'도움말',start:'시작 안내',topic:'대화 주제',discard:'대기 요청 취소',pause:'일시정지',approve:'실행 허용',deny:'실행 거절',sethome:'메신저 기본 대화',restart:'연결 서비스 재시작',platform:'메신저 선택'};
const categoryIcons:Record<string,LucideIcon>={Session:MessageSquare,Configuration:Settings,Info:Activity,'Tools & Skills':Plug,Exit:LogOut,TUI:Terminal};
const icons:Record<string,LucideIcon>={new:Plus,model:Cpu,memory:Brain,skills:BookOpen,goal:Target,loop:Repeat2,status:Activity};
type Props={text:string;draft:(text:string)=>void;execute:(command:string)=>void;busy?:boolean};
export function useChatCommands(props:Props){
 const [catalog,setCatalog]=useState<CommandCatalog>(),[error,setError]=useState(''),[index,setIndex]=useState(0),[dismissed,setDismissed]=useState<string>();
 const slash=props.text.startsWith('/')&&!props.text.includes('\n'),query=props.text.slice(1).toLocaleLowerCase(),space=query.indexOf(' '),base=space<0?query:query.slice(0,space);
 const open=slash&&dismissed!==props.text;
 useEffect(()=>{if(!open)return;let live=true;void commandCatalog().then(value=>{if(live){setCatalog(value);setError('')}}).catch(error=>{if(live)setError(String(error.message||error))});return()=>{live=false}},[open]);
 const canonical=catalog?.canon['/'+base]||'/'+base;
 const entries=space>=0?(catalog?.sub[canonical]||[]).map(option=>[canonical+' '+option,option] as [string,string]):catalog?.pairs||[];
 const items=entries.map(([command,description])=>{const name=command.slice(1).split(' ')[0],skill=!!catalog?.skills[command];return {command,description,label:space>=0?command.slice(canonical.length+1):names[name]||(skill?'스킬 · ':'명령 · ')+name,name,skill}}).filter(item=>{
  const needle=space>=0?query.slice(space+1).trim():query.trim();
  return !needle||(item.command+' '+item.label+' '+item.description).toLocaleLowerCase().includes(needle);
 });
 const visible=open&&(space<0||items.length>0);
 useEffect(()=>{setIndex(0)},[props.text]);
 useEffect(()=>{if(visible)document.getElementById('hermes-command-option-'+index)?.scrollIntoView({block:'nearest'})},[index,visible]);
 const execute=(command:string)=>{const space=command.indexOf(' '),name=space<0?command:command.slice(0,space);props.execute((catalog?.canon[name]||name)+(space<0?'':command.slice(space)))};
 const pick=(command:string)=>{
  if(props.busy)return;
  const name=command.split(' ')[0],meta=catalog?.commands[name];
  if(meta?.argument_mode&&!command.includes(' ')&&!['/model','/new','/clear','/history','/sessions'].includes(name)){props.draft(command+' ');return}
  props.draft('');execute(command);
 };
 const accept=()=>{
  if(!slash)return false;
  if(props.busy)return true;
  if(space>=0&&visible&&items.length&&!items.some(item=>item.command===props.text.trim())){pick(items[Math.min(index,items.length-1)].command);return true}
  if(space>=0||catalog?.canon['/'+query.trim()]||catalog?.pairs.some(([key])=>key==='/'+query.trim())){execute(props.text.trim());props.draft('');return true}
  if(items.length)pick(items[Math.min(index,items.length-1)].command);else if(query.trim()){execute(props.text.trim());props.draft('')}
  return true;
 };
 const keyDown=(event:KeyboardEvent<HTMLTextAreaElement>)=>{
  if(!slash||event.nativeEvent.isComposing)return false;
  if(event.key==='Escape'&&open){event.preventDefault();setDismissed(props.text);return true}
  if(visible&&(event.key==='ArrowDown'||event.key==='ArrowUp')){event.preventDefault();setIndex(value=>items.length?(value+(event.key==='ArrowDown'?1:-1)+items.length)%items.length:0);return true}
  if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();accept();return true}
  return false;
 };
 const menu=visible?<div id="hermes-command-menu" role="listbox" aria-label="대화 기능" className="ui-command-menu">
  {error?<p role="alert" className="p-3 text-sm text-rose-600">공식 명령을 불러오지 못했습니다: {error}</p>:!catalog?<p className="p-3 text-sm text-slate-500">공식 기능을 불러오는 중…</p>:items.length?items.map((item,i)=>{const category=catalog.categories?.find(group=>group.pairs.some(([key])=>key===item.command))?.name||'';const Icon=icons[item.name]||(item.skill?BookOpen:categoryIcons[category]||Terminal);return <Button id={'hermes-command-option-'+i} key={item.command} type="button" role="option" aria-selected={i===index} variant="ghost" className={'ui-command-option '+(i===index?'is-selected':'')} title={item.description} onMouseEnter={()=>setIndex(i)} onMouseDown={event=>event.preventDefault()} onClick={()=>pick(item.command)}><Icon size={18}/><span>{item.label}</span><small>{item.command}</small>{catalog.commands[item.command]?.argument_mode&&<ChevronRight size={14} className="ml-auto"/>}</Button>}):<p className="p-3 text-sm text-slate-500">일치하는 기능이 없습니다.</p>}
 </div>:null;
 return {open:visible,menu,keyDown,accept};
}
