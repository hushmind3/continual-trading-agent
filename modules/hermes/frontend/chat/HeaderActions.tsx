import type {Ref} from 'react';
import {Plus,PanelRight,Maximize2,Minimize2,Settings2,BriefcaseBusiness} from 'lucide-react';
import {Button,IconButton} from '@platform/ui/Primitives';
interface Props {
 pending:boolean;create:()=>void;activityButton:Ref<HTMLButtonElement>;
 activityOpen:boolean;toggleActivity:()=>void;focused:boolean;
 onFocus:()=>void;onSettings:()=>void;
 company?:{open:boolean;toggle:()=>void};
}
export function HeaderActions({pending,create,activityButton,activityOpen,toggleActivity,focused,onFocus,onSettings,company}:Props){
 return <div className="ha-heading-actions">
  <Button aria-label="새 대화 만들기" title="새 대화" disabled={pending} onClick={create}><Plus size={18}/><span>새 대화</span></Button>
  {company&&<IconButton title="사업 초안·진행" aria-label="사업 관리 보기" aria-pressed={company.open} onClick={company.toggle}><BriefcaseBusiness size={18}/></IconButton>}
  <IconButton ref={activityButton} title="작업 내역" aria-label="작업 내역 보기" aria-pressed={activityOpen} onClick={toggleActivity}><PanelRight size={18}/></IconButton>
  <IconButton title={focused?'집중 모드 나가기':'집중 모드'} aria-label={focused?'집중 모드 나가기':'집중 모드 켜기'} aria-pressed={focused} onClick={onFocus}>{focused?<Minimize2 size={18}/>:<Maximize2 size={18}/>}</IconButton>
  <IconButton title="설정" aria-label="설정 열기" onClick={onSettings}><Settings2 size={18}/></IconButton>
 </div>;
}
