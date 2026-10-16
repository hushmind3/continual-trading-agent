import {contentText, type Message} from '../types';

export function engineNote(message: Message) {
  const text = contentText(message.content).trimStart();
  return text.startsWith('[CONTEXT COMPACTION — REFERENCE ONLY]')
    || text.startsWith('[System: Your previous response was truncated by the output length limit.');
}
export function EngineNotes({messages}: {messages: Message[]}) {
  const notes = messages.filter(engineNote);
  return notes.length ? <details className="ha-engine-notes">
    <summary>대화 정리 기록 · {notes.length}개</summary>
    <p>긴 대화를 이어가기 위해 엔진이 남긴 내부 요약입니다. 사용자 메시지와 답변은 대화창에 유지됩니다.</p>
    {notes.map((message, index) => <pre key={index}>{contentText(message.content)}</pre>)}
  </details> : null;
}
