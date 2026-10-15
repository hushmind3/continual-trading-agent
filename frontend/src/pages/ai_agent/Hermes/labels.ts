export const toolLabels:Record<string,string>={write_file:'파일 저장',read_file:'파일 읽기',patch:'코드 수정',search_files:'파일 검색',terminal:'명령 실행',process_manage:'실행 관리',todo_list:'작업 계획',skill_view:'스킬 읽기',skills_list:'스킬 검색',skill_manage:'스킬 관리',computer_use:'컴퓨터 조작',browser_exec:'브라우저 조작',tool_search:'외부 도구 검색',tool_describe:'도구 사용법 확인',tool_call:'외부 도구 실행'};
export const eventLabels:Record<string,string>={starting:'작업 준비',running:'작업 중',complete:'작업 완료',failed:'작업 실패',stopped:'작업 중지',tool_start:'도구 실행',tool_complete:'도구 실행 완료',status:'진행 상황',thinking:'생각 정리',reasoning:'계획 수립'};
export function toolLabel(name:string){return toolLabels[name]??(name.startsWith('mcp')?'외부 도구':name.startsWith('browser')?'브라우저 조작':name)}
export function eventSummary(name:string,detail:string){
 try{const value=JSON.parse(detail);if(Array.isArray(value)&&typeof value[1]==='string')return toolLabel(value[1]);if(name==='starting'&&value.model)return '사용 모델 · '+String(value.model)}catch{/* Original text remains available in the detail disclosure. */}
 return eventLabels[name]??'작업 진행';
}
