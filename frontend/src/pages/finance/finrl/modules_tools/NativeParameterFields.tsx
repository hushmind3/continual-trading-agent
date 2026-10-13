import {inputClass,ErrorMessage} from '../../../../ui/Primitives';
export interface NativeParameter {name:string;annotation?:string;required:boolean;default?:string;kind?:string}
export function NativeParameterFields({title,parameters,value,onChange}:{title:string;parameters:NativeParameter[];value:string;onChange:(value:string)=>void}){
 let values:Record<string,unknown>;
 try{values=JSON.parse(value);if(values==null||Array.isArray(values)||typeof values!=='object')throw new Error()}catch{return <ErrorMessage message={title+': 고급 JSON 입력을 먼저 확인하세요.'}/>}
 const update=(parameter:NativeParameter,text:string)=>{
  const next={...values};
  if(!text.trim())delete next[parameter.name];
  else if(text.startsWith('$'))next[parameter.name]=text;
  else if(/bool/i.test(parameter.annotation??''))next[parameter.name]=text==='true';
  else if(/^(int|float)$/.test(parameter.annotation??'')||/^[-+]?\d+(\.\d+)?$/.test(parameter.default??''))next[parameter.name]=Number.isFinite(Number(text))?Number(text):text;
  else if(/^[\[{]/.test(text)){try{next[parameter.name]=JSON.parse(text)}catch{next[parameter.name]=text}}
  else if(!parameter.annotation&&!/^['"]/.test(parameter.default??'')){try{next[parameter.name]=JSON.parse(text)}catch{next[parameter.name]=text}}
  else next[parameter.name]=text;
  onChange(JSON.stringify(next,null,2));
 };
 if(!parameters.length)return null;
 return <details open className="my-3 text-xs text-slate-600"><summary>{title} · 필수·선택 입력 전체</summary><div className="mt-3 grid gap-3 sm:grid-cols-2">{parameters.map(parameter=>{
  const current=values[parameter.name],text=current==null?'':typeof current==='object'?JSON.stringify(current):String(current);
  return <label key={parameter.name}>{parameter.name}{parameter.required?' · 필수':' · 선택'}<span className="ml-2 text-slate-400">{parameter.annotation||'원본 타입'}</span>
   {parameter.kind?.includes('VAR_')?<p className="mt-1">가변 인자는 고급 JSON에서 입력</p>:/bool/i.test(parameter.annotation??'')?<select className={inputClass+' mt-1'} value={text} onChange={e=>update(parameter,e.target.value)}><option value="">원본 기본값 사용</option><option value="true">true</option><option value="false">false</option></select>:<input className={inputClass+' mt-1'} value={text} onChange={e=>update(parameter,e.target.value)} placeholder={parameter.default==null?'비우면 원본 기본값':parameter.default}/>}
  </label>;
 })}</div></details>;
}
