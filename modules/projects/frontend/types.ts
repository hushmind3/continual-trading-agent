export interface Project {id:string;title:string;repository:string;url:string;stage:string;detail:string;error?:string;active_source?:string;source?:string;module_id?:string;menu?:string;adapter?:{kind:string;ui?:unknown};agent_session?:string;environment_keys?:string[];log?:string;builtin?:boolean;group_title?:string;can_open?:boolean;allow_agent?:boolean;standalone_path?:string;connection_error?:string;connection_pending?:boolean;verification?:{entry_executed?:boolean;original_ui_rendered?:boolean}}
export interface Repository {repository:string;url:string;description:string;stars:number;language:string;updated_at:string}
export const stages:Record<string,string>={queued:'준비',download:'다운로드',analyze:'구조 분석',adapter:'자동 변환',dependencies:'의존성·빌드',verify:'실행 확인',publish:'연결 준비',awaiting_activation:'메뉴 연결 중',ready:'사용 가능',failed:'설치 실패',cancelled:'취소됨',removed:'분리됨'};
export const working=(stage:string)=>!['ready','failed','cancelled','removed','needs_adapter','removal_failed','not_app'].includes(stage);
stages.needs_adapter='실행 연결 필요';
stages.removal_failed='제거 재시도 필요';
stages.agent_link='에이전트·화면 연결';

stages.detaching="분리 준비 중";
stages.not_app='실행 앱 없는 자료';
