import {useEffect,useState,type KeyboardEvent} from 'react';
import {Button} from '@platform/ui/Primitives';
import {Plus,Cpu,Brain,Target,Repeat2,Activity,Plug,BookOpen,type LucideIcon} from 'lucide-react';
import {navigateAgent,openOfficial} from '../agent_navigation';

type Action={id:string;label:string;description?:string;icon:LucideIcon;run:()=>void};
type Props={text:string;draft:(text:string)=>void;model:()=>void;mode:(mode:string)=>void;create:()=>void;activity:()=>void;business?:()=>void};
export function useChatCommands(props:Props){
 const [index,setIndex]=useState(0),[dismissed,setDismissed]=useState<string>();
 const actions:Action[]=[
  {id:'model',label:'모델',icon:Cpu,description:'사용할 모델 선택',run:props.model},
  {id:'mcp',label:'도구 연결',icon:Plug,description:'MCP 서버 관리',run:()=>navigateAgent('settings','mcp')},
  {id:'memory',label:'메모리',icon:Brain,description:'기억 설정 열기',run:()=>openOfficial('/config')},
  {id:'skills',label:'스킬',icon:BookOpen,description:'작업 지침 관리',run:()=>navigateAgent('settings','skills')},
  {id:'goal',label:'목표',icon:Target,description:'목표를 정해 실행',run:()=>props.mode('goal')},
  {id:'loop',label:'반복 실행',icon:Repeat2,description:'실행 주기 설정',run:()=>props.mode('loop')},
  {id:'status',label:'상태',icon:Activity,description:'현재 작업 확인',run:props.activity},
  {id:'new',label:'새 대화',icon:Plus,description:'새 대화 시작',run:props.create},
 ];
 const query=props.text.slice(1).toLocaleLowerCase().trim();
 const open=props.text.startsWith('/')&&!props.text.includes('\n')&&dismissed!==props.text;
 const items=actions.filter(item=>!query||(item.id+' '+item.label+' '+(item.description||'')).toLocaleLowerCase().includes(query));
 useEffect(()=>{setIndex(0)},[props.text]);
 const pick=(item:Action)=>{props.draft('');item.run()};
 const accept=()=>{if(!open)return false;if(items.length)pick(items[Math.min(index,items.length-1)]);return true};
 const keyDown=(event:KeyboardEvent<HTMLTextAreaElement>)=>{
  if(!open||event.nativeEvent.isComposing)return false;
  if(event.key==='Escape'){event.preventDefault();setDismissed(props.text);return true}
  if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();setIndex(value=>items.length?(value+(event.key==='ArrowDown'?1:-1)+items.length)%items.length:0);return true}
  if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();accept();return true}
  return false;
 };
 const menu=open?<div id="hermes-command-menu" role="listbox" aria-label="대화 기능" className="ui-command-menu">
  {items.length?items.map((item,i)=>{const Icon=item.icon;return <Button key={item.id} type="button" role="option" aria-selected={i===index} variant="ghost" className={'ui-command-option '+(i===index?'is-selected':'')} onMouseDown={event=>event.preventDefault()} onClick={()=>pick(item)}><Icon size={18}/><span>{item.label}</span>{item.description&&<small>{item.description}</small>}</Button>}):<p className="p-3 text-sm text-slate-500">일치하는 기능이 없습니다. 다른 이름으로 검색하거나 Esc로 닫으세요.</p>}
 </div>:null;
 return {open,menu,keyDown,accept};
}
