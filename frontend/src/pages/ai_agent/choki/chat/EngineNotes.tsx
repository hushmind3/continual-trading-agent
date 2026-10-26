import {contentText, type Message} from '../types';
import {toolLabel} from '../labels';

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

export function displayEngineResponse(text:string){
 if(text.startsWith('Model output entered a repetition loop'))return '모델이 같은 출력을 반복해 응답 생성을 중단했습니다. 요청 처리는 완료되지 않았습니다. 저장된 발언과 작업 기록은 유지됩니다.';
 const stopped=/^I stopped retrying because I kept running ([\w.-]+) (\d+) times without making progress\./.exec(text);
 return stopped?`${toolLabel(stopped[1])} 요청이 같은 원인으로 ${stopped[2]}회 반복 실패해 멈췄습니다. 작업은 완료되지 않았습니다. 실행 과정을 펼쳐 오류를 확인하고 요청 내용을 수정해 주세요.`:text;
}
