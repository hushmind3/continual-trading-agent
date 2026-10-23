import {Button,Drawer,ErrorMessage,Input,Textarea} from '@platform/ui/Primitives';
interface Props {
 creating:boolean;editing:boolean;pending:boolean;error:string;
 name:string;group:string;description:string;body:string;
 setName:(value:string)=>void;setGroup:(value:string)=>void;
 setDescription:(value:string)=>void;setBody:(value:string)=>void;
 setEditing:(value:boolean)=>void;save:()=>Promise<void>;
}
export function SkillEditor({creating,editing,pending,error,name,group,description,body,setName,setGroup,setDescription,setBody,setEditing,save}:Props){
 return (<Drawer title={creating?'새 스킬 만들기':'스킬 내용 수정'} open={editing} onClose={()=>{if(!pending)setEditing(false)}}><form className="ui-settings-fields" onSubmit={event=>{event.preventDefault();void save()}}>
 <div className="hermes-section-heading"><h3>{creating?'스킬 만들기':name+' 수정'}</h3><Button disabled={pending} onClick={()=>setEditing(false)}>닫기</Button></div>{creating&&<><label>이름 · 영문 식별자<Input required pattern="[a-z0-9][a-z0-9_-]*" value={name} onChange={e=>setName(e.target.value)}/></label><label>분류 · 영문 폴더<Input required value={group} onChange={e=>setGroup(e.target.value)}/></label><label>설명 · 언제 사용하는 스킬인가요?<Textarea required rows={2} value={description} onChange={e=>setDescription(e.target.value)}/></label></>}<label>{creating?'작업 지침':'SKILL.md 원문'}<Textarea aria-label="스킬 작업 지침" required rows={14} value={body} onChange={e=>setBody(e.target.value)}/></label><ErrorMessage message={error}/><Button type="submit" tone="primary" disabled={pending} busy={pending}>저장</Button></form></Drawer>);
}
