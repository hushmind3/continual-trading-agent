import {useLayoutEffect, useRef, useState, type RefObject} from 'react';
import {Sparkles, Square, ArrowUp, Paperclip} from 'lucide-react';
import {Button, Input, Select, Textarea} from '@platform/ui/Primitives';
import {ComposerFrame} from '@platform/ui/ComposerFrame';
import {FileChips, type AttachedFile} from '@platform/ui/FileChips';
import {RunModeOptions} from './RunModeOptions';
import {ToggleSwitch} from '@platform/ui/ToggleSwitch';
import {ThinkingControl} from './ThinkingControl';
import type {ThinkingMode} from './useThinking';
import type {ReasoningSelection} from '../settings/models/ReasoningSelect';
export type Attachment = AttachedFile;
interface Props {
 company?:boolean;conversationId?:string;companySources?:{session_id:string;title:string}[];onConversation?:(id:string)=>void;
 attachments: Attachment[]; uploading: boolean; upload: (files: File[]) => void; removeAttachment: (path: string) => void;
 composer: RefObject<HTMLTextAreaElement|null>; text: string; draft: (value: string) => void; send: () => void; stop: () => void;
 blocked?:boolean;canSteer?:boolean;active: boolean; pending: boolean; stopping: boolean; mode: string; setMode: (value: string) => void;
 turns: number; setTurns: (value: number) => void; interval: number; setIntervalSeconds: (value: number) => void;
 times: number; setTimes: (value: number) => void;
 readOnly:boolean;setReadOnly:(value:boolean)=>void;
 thinking:ThinkingMode;setThinking:(value:ThinkingMode)=>void;localThinking:boolean;
 reasoning?:ReasoningSelection;
}
export function ChatComposer(props: Props) {
 const {attachments, uploading, upload, removeAttachment, composer, text, draft, send, stop, active, pending, stopping, mode, setMode,readOnly,setReadOnly} = props;
 const fileInput = useRef<HTMLInputElement>(null), dragDepth = useRef(0);
 const [dragging, setDragging] = useState(false);
 useLayoutEffect(() => {
  const element = composer.current;
  if (!element) return;
  const style = getComputedStyle(element);
  element.style.height = 'auto';
  element.style.height = Math.min(parseFloat(style.maxHeight), Math.max(parseFloat(style.minHeight), element.scrollHeight)) + 'px';
 }, [composer, text]);
 return <ComposerFrame dragging={dragging} onSubmit={event => {event.preventDefault(); send();}}
  onDragOver={event => {if (event.dataTransfer.types.includes('Files')) {event.preventDefault(); event.dataTransfer.dropEffect='copy'; if (!dragDepth.current) {dragDepth.current=1; setDragging(true);}}}}
  onDragLeave={event => {if (!event.currentTarget.contains(event.relatedTarget as Node)) {dragDepth.current=0; setDragging(false);}}}
  onDrop={event => {event.preventDefault(); dragDepth.current=0; setDragging(false); const files=Array.from(event.dataTransfer.files); if(files.length)upload(files);}}
  attachments={<FileChips files={attachments} remove={removeAttachment}/>}
  toolbar={<>
   <Button type="button" variant="ghost" data-composer-action="attach" aria-label="파일 첨부" title="파일 첨부 · 끌어놓기와 붙여넣기도 가능" busy={uploading} disabled={uploading} onClick={() => fileInput.current?.click()}><Paperclip size={18}/></Button>
   {!!props.companySources?.length&&<label className="ha-mode-select ha-conversation-select"><span>대상</span><Select aria-label="대화 대상" disabled={pending} value={props.company?props.conversationId:''} onChange={event=>props.onConversation?.(event.target.value)}><option value="">일반 대화</option>{props.companySources.map(source=><option key={source.session_id} value={source.session_id}>{source.title}</option>)}</Select></label>}
   <label className="ha-mode-select"><Sparkles size={14}/><Select aria-label="실행 방식" title={active?'다음 요청의 실행 방식':'실행 방식'} disabled={pending} value={mode} onChange={event=>setMode(event.target.value)}><option value="chat">한 번 실행</option><option value="goal">목표 달성까지</option><option value="loop">반복 실행</option></Select></label>
   <ToggleSwitch label="읽기 모드" checked={readOnly} onChange={setReadOnly} title={active?'다음 요청부터 적용 · 켜면 파일 읽기·검색만 허용합니다':'켜면 파일 읽기·검색만 허용합니다. 끄면 선택한 도구를 사용할 수 있습니다.'}/>
   <ThinkingControl value={props.thinking} change={props.setThinking} local={props.localThinking} active={active} reasoning={props.reasoning}/>
   <span className="ui-composer-key-hint">{active?'Enter로 작업 중 메시지 전달':'Enter 전송 · Shift+Enter 줄바꿈'}</span>
   {active&&<Button data-composer-action="stop" tone="danger" aria-label="작업 중지" busy={pending} disabled={pending||stopping} onClick={stop}><Square size={16}/><span>{stopping?'중지 중':'중지'}</span></Button>}
   <Button data-composer-action="send" type="submit" aria-label="메시지 보내기" title={active?'작업 중 메시지 전달':'보내기'} tone="primary" busy={pending} disabled={props.blocked||pending||stopping||active&&props.canSteer===false||uploading||(!text.trim()&&!attachments.length)}><ArrowUp size={19}/></Button>
  </>}
  options={<RunModeOptions {...props}/>}
 >
  <Input ref={fileInput} type="file" multiple className="hidden" aria-label="첨부 파일 선택" onChange={event => {upload(Array.from(event.target.files??[])); event.target.value='';}}/>
  <Textarea ref={composer} aria-label="헤르메스에게 보낼 메시지" placeholder={active?'작업 중에도 질문하거나 지시를 추가하세요…':props.company?'AI 총괄에게 질문하거나 업무를 지시하세요…':'무엇을 함께 해볼까요?'} value={text} onChange={event => draft(event.target.value)} rows={1}
   onPaste={event => {const files=Array.from(event.clipboardData.files); if (files.length) {event.preventDefault(); upload(files);}}}
   onKeyDown={event => {if(event.key==='Enter'&&!event.shiftKey&&!event.nativeEvent.isComposing) {event.preventDefault(); send();}}}/>
 </ComposerFrame>;
}
