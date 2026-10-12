import {useSystemState} from '../../data/Operations';
import {Panel,KeyValues} from '../../ui/Panel';
import {ErrorMessage} from '../../ui/Primitives';
import {NativeModuleRunner} from './NativeModuleRunner';
interface ModuleInfo {
 id:string;path:string;framework:string;description?:string;status?:string;reason?:string;
 functions:string[];signatures:Record<string,string>;parameters?:Record<string,{name:string;annotation?:string;required:boolean;default?:string}[]>;
 dependencies?:string[];imports?:string[];calls?:string[];actions?:string[];verified_functions?:string[];
 native_api?:string|null;last_error?:string;file?:string;
}
export function SourceModuleWorkspace(){
 const catalog=useSystemState<{items:ModuleInfo[]}>('framework');
 const id=decodeURIComponent(location.hash.replace(/^#source-module-/,'').split('?')[0]);
 const module=catalog.data?.items.find(item=>item.id===id);
 const area=module?.framework==='FinRL'?'FinRL · 메인 소스':module?.framework==='FinRL-X'?'FinRL-Trading · 보조 소스':'프로젝트 · 백엔드 소스';
 if(!module)return <Panel title="소스 모듈 조회"><ErrorMessage message={catalog.error}/><p className="text-xs">{catalog.loading?'설치된 소스 정보를 읽는 중입니다.':'현재 설치 목록에서 이 모듈을 찾지 못했습니다.'}</p></Panel>;
 const functions=module.functions??[];
 return <div className="space-y-3">
  <Panel title={module.path} description="설치된 소스의 탐색 화면입니다. 메뉴 표시·코드 존재·실제 실행 성공은 구분합니다.">
   <ErrorMessage message={catalog.error||module.last_error||''}/>
   <KeyValues items={[['영역',area],['모듈 ID',module.id],['현재 상태',module.status??'실행 미확인'],['연결 사유',module.reason??'확인된 실행 기록 없음'],['공개 함수·클래스',String(functions.length)],['실행 기록',module.verified_functions?.join(', ')||'성공 기록 없음']]}/>
   <h3 className="my-2 text-sm font-semibold">원본 설명</h3><p className="whitespace-pre-wrap text-xs text-slate-600">{module.description||'원본에 모듈 설명이 없습니다.'}</p>
   <p className="mt-3 text-xs text-slate-500">등록된 실행 작업: {module.actions?.join(', ')||'전용 실행 작업 없음'}</p>
  </Panel>
  <Panel title="공개 함수·클래스 · 입력 항목">
   {!functions.length&&<p className="text-xs text-slate-500">공개 함수 선언이 없는 소스도 목록에 유지합니다.</p>}
   {functions.map(name=>{
    const parameters=module.parameters?.[name]??module.parameters?.[name+'.__init__']??[];
    return <details key={name} className="border-b border-slate-100 py-2"><summary className="break-all text-xs font-medium">{name}({module.signatures?.[name]??''})</summary>
     <div className="mt-2 overflow-auto"><table className="w-full text-left text-xs"><thead className="text-slate-500"><tr><th>입력 이름</th><th>원본 타입</th><th>필수 여부</th><th>원본 기본값</th></tr></thead><tbody>{parameters.map(parameter=><tr className="border-t border-slate-100" key={parameter.name}><td className="py-2">{parameter.name}</td><td>{parameter.annotation||'명시 없음'}</td><td>{parameter.required?'필수':'선택'}</td><td>{parameter.default??'없음'}</td></tr>)}</tbody></table>{!parameters.length&&<p className="text-slate-500">추출된 입력 항목 없음 · 함수 서명을 확인하세요.</p>}</div>
    </details>;
   })}
  </Panel>
  <Panel title="의존성·호출 관계"><p className="break-words text-xs">{(module.dependencies??module.imports??[]).join(' → ')||'기록된 의존성 없음'}</p><details className="mt-2 text-xs"><summary>호출 목록 펼치기</summary><pre className="mt-2 overflow-auto whitespace-pre-wrap">{module.calls?.join('\n')||'기록된 호출 없음'}</pre></details></Panel>
  {module.native_api&&(module.framework==='FinRL'||module.framework==='FinRL-X')?<NativeModuleRunner key={module.id} framework={module.framework} selectedModule={module.id} onSelect={selected=>{location.hash='source-module-'+encodeURIComponent(selected)}}/>:
   <Panel title="실행 연결 상태" description={module.reason||'이 모듈에 원본 함수 직접 실행 연결이 없습니다.'}><p className="text-xs">실행되지 않는 모듈도 폐기 판단을 위해 메뉴에 표시합니다. 소속 작업 또는 등록 API에서 실행할 수 있는지 확인합니다.</p><a className="mt-2 inline-block text-xs text-blue-700" href="#backend-browser?tab=commands">등록된 API·기능 확인 →</a></Panel>}
 </div>;
}
