import {useState} from 'react';
import {useOperations,useSystemState} from '../../data/Operations';
import {apiUrl} from '../../data/api';
import type {BackendMenuCatalog,JsonSchema} from '../../data/menu_types';
import {FrameworkTools} from './FrameworkTools';
import {ModuleCatalog} from './FrameworkWorkspace';
import {Panel} from '../../ui/Panel';
import {Button,ErrorMessage,Tabs,inputClass} from '../../ui/Primitives';

function fields(schema:JsonSchema,values:Record<string,unknown>,update:(values:Record<string,unknown>)=>void){
 return Object.entries(schema.properties??{}).map(([name,original])=>{
  const actual=original.$ref?schema.$defs?.[original.$ref.split('/').pop()??'']??original:original;
  const property=actual.anyOf?.find(item=>item.type!=='null')??actual;
  const value=values[name],choices=property.enum??(property.type==='boolean'?[true,false]:undefined);
  const change=(text:string)=>{
   const next={...values};
   if(!text.trim())delete next[name];
   else if(property.type==='boolean')next[name]=text==='true';
   else if(property.type==='number'||property.type==='integer')next[name]=text;
   else if(property.type==='array'&&property.items?.type==='string')next[name]=text.split(',').map(item=>item.trim()).filter(Boolean);
   else if(property.type==='array'||property.type==='object')next[name]=text;
   else next[name]=text;
   update(next);
  };
  const displayed=value==null?'':Array.isArray(value)&&property.items?.type==='string'?value.join(', '):typeof value==='object'?JSON.stringify(value):String(value);
  return <label key={name} className="min-w-0 text-xs text-slate-600">{name}{schema.required?.includes(name)?' · 필수':' · 선택'}<span className="ml-2 text-slate-400">{property.type??'원본 타입'}</span>
   {choices?<select className={inputClass+' mt-1'} value={displayed} onChange={e=>change(e.target.value)}><option value="">원본 기본값 사용</option>{choices.map(choice=><option key={String(choice)} value={String(choice)}>{String(choice)}</option>)}</select>:
   <input className={inputClass+' mt-1'} type={/secret|password|token|app_key/i.test(name)?'password':property.type==='number'||property.type==='integer'?'number':'text'} min={property.minimum} max={property.maximum} value={displayed} placeholder={property.type==='array'?'문자 목록은 쉼표로 구분 · 기타 배열은 JSON':property.type==='object'?'JSON 객체':property.default==null?'비우면 원본 기본값':String(property.default)} onChange={e=>change(e.target.value)}/>}
   {property.description&&<span className="mt-1 block">{property.description}</span>}
  </label>;
 });
}

export function FeatureWorkspace(){
 const catalog=useSystemState<BackendMenuCatalog>('menu_catalog'),{execute,pending}=useOperations();
 const [tab,setTab]=useState('features'),[query,setQuery]=useState(''),[commandKey,setCommandKey]=useState(''),[paths,setPaths]=useState<Record<string,unknown>>({}),[payload,setPayload]=useState<Record<string,unknown>>({}),[raw,setRaw]=useState('{}'),[error,setError]=useState(''),[result,setResult]=useState<unknown>();
 const actionId=location.hash.replace(/^#feature-/,'').split('?')[0],action=catalog.data?.actions.find(item=>item.id===actionId);
 const commands=catalog.data?.commands??[],command=commands.find(item=>item.operation+'|'+item.methods.join(',')===commandKey)??commands[0];
 const operation=command?.operation.replace(/\{([^}:]+)(?::[^}]+)?\}/g,(_,key:string)=>String(paths[key]??''));
 const schema=command?.methods.includes('POST')?command.body_schema:command?.query_schema;
 const structured=!!Object.keys(schema?.properties??{}).length;
 const run=async()=>{
  if(!command||!operation)return;setError('');setResult(undefined);
  try{
   for(const name of command.path_schema.required??[])if(paths[name]==null||paths[name]==='')throw new Error('경로 입력이 필요합니다: '+name);
   const args=structured?{...payload}:JSON.parse(raw);
   if(args==null||typeof args!=='object'||Array.isArray(args))throw new Error('입력은 JSON 객체여야 합니다.');
   if(structured)for(const [name,property] of Object.entries(schema?.properties??{})){
    const type=(property.anyOf?.find(item=>item.type!=='null')??property).type;
    if(args[name]!=null&&typeof args[name]==='string'&&(type==='object'||type==='array'))args[name]=JSON.parse(args[name] as string);
    if(args[name]!=null&&(type==='number'||type==='integer')){const number=Number(args[name]);if(!Number.isFinite(number))throw new Error(name+': 숫자를 입력하세요.');args[name]=number;}
   }
   setResult(await execute(operation,args,command.methods.includes('POST')?'POST':'GET'));
  }catch(e){setError(e instanceof Error?e.message:'실행 실패')}
 };
 if(action)return <div className="space-y-3"><Panel title={action.name} description="백엔드에 실제 등록된 기능입니다. 등록 여부와 실제 실행 성공은 구분합니다.">
  <p className="text-xs text-slate-600">소속: {catalog.data?.groups.find(group=>group.id===action.group)?.title} · 원본: {action.module} · 함수: {action.function}</p>
  {action.id==='finrl_workflow'&&<p className="mt-2 text-xs text-amber-700">공식 CLI의 기존 기본값을 사용합니다. 기존 중앙 SAC 학습은 정책 학습 화면에서 실행합니다.</p>}
 </Panel><FrameworkTools key={action.id} menu={action.menu} framework={action.group==='finrl_trading'?'FinRL-X':action.group==='finrl'?'FinRL':undefined} actionId={action.id}/></div>;
 return <div className="space-y-3">
  <Panel title="백엔드 기능 전체" description="등록된 기능·API·원본 모듈을 확인하고 필요한 항목을 선택합니다. 목록에서 임의로 기능을 제거하지 않습니다.">
   <ErrorMessage message={catalog.error}/>
   <Tabs value={tab} onChange={setTab} items={[{id:'features',label:'큰 메뉴 · 전체 기능'},{id:'commands',label:'등록된 API · 입력값'},{id:'modules',label:'원본 모듈 · 함수'}]}/>
   <input className={inputClass+' mt-3 max-w-md'} value={query} onChange={e=>setQuery(e.target.value)} placeholder="기능·메뉴·모듈·API 검색" aria-label="백엔드 기능 검색"/>
  </Panel>
  {tab==='features'&&catalog.data?.groups.map(group=>{
   const actions=catalog.data?.actions.filter(item=>item.group===group.id&&(!query||(item.name+' '+item.module+' '+item.function).toLowerCase().includes(query.toLowerCase())))??[];
   const menus=group.menus.filter(item=>!query||(item.title+' '+item.operations.join(' ')).toLowerCase().includes(query.toLowerCase()));
   if(!menus.length&&!actions.length)return null;
   return <Panel key={group.id} title={group.title} description={'기존 화면 '+group.menus.length+'개 · 등록된 추가 작업 '+(catalog.data?.actions.filter(item=>item.group===group.id).length??0)+'개'}>
    <div className="grid gap-2 sm:grid-cols-2">{menus.map(menu=><a className="rounded border border-slate-200 p-2 text-xs hover:bg-blue-50" key={menu.id} href={'#'+menu.id}><b>{menu.title}</b><span className="mt-1 block text-slate-500">화면: {menu.frontend}</span><span className="block text-slate-500">연결: {menu.manager}</span></a>)}</div>
    <div className="mt-3 overflow-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b text-slate-500"><th>추가 기능</th><th>원본·함수</th><th>입력 항목</th><th>연결</th></tr></thead><tbody>{actions.map(item=><tr className="border-b border-slate-100" key={item.id}><td className="p-2">{item.name}</td><td className="p-2 break-all">{item.module}<br/>{item.function}</td><td className="p-2">{item.fields.join(', ')||'입력 없음'}</td><td className="p-2">{['stock_data','stock_train','stock_backtest','native_call'].includes(item.id)?<a className="text-blue-700" href={'#'+(item.id==='stock_data'?'finrl':item.id==='stock_train'?'stock-training':item.id==='stock_backtest'?'backtest':'project-modules')}>기존 화면</a>:<a className="text-blue-700" href={'#feature-'+item.id}>기능 열기</a>}</td></tr>)}</tbody></table></div>
   </Panel>;
  })}
  {tab==='commands'&&<Panel title="등록된 API · 전체 입력값" description="기존 단일 API를 사용합니다. 입력을 비우면 해당 API의 원본 기본값을 사용합니다.">
   <select className={inputClass} value={command?command.operation+'|'+command.methods.join(','):''} onChange={e=>{setCommandKey(e.target.value);setPaths({});setPayload({});setRaw('{}');setError('');setResult(undefined)}} aria-label="API 선택">{commands.filter(item=>!query||(item.operation+' '+item.function).toLowerCase().includes(query.toLowerCase())).map(item=><option key={item.operation+'|'+item.methods.join(',')} value={item.operation+'|'+item.methods.join(',')}>{item.operation} · {item.methods.join(', ')}</option>)}</select>
   <p className="my-2 break-all text-xs text-slate-500">{command?.module} · {command?.function} · {catalog.data?.groups.find(group=>group.id===command?.group)?.title}</p>
   {command?.description&&<details className="mb-3 text-xs text-slate-500"><summary>원본 설명</summary><p className="mt-2 whitespace-pre-wrap">{command.description}</p></details>}
   {command&&<div className="mb-3 grid gap-3 sm:grid-cols-2">{fields(command.path_schema,paths,setPaths)}</div>}
   {schema&&structured?<div className="mb-3 grid gap-3 sm:grid-cols-2">{fields(schema,payload,setPayload)}</div>:<label className="block text-xs text-slate-600">전체 입력 JSON<textarea className={inputClass+' my-2 min-h-24 font-mono'} value={raw} onChange={e=>setRaw(e.target.value)}/></label>}
   <details className="my-3 text-xs text-slate-500"><summary>전체 입력 계약</summary><pre className="mt-2 overflow-auto whitespace-pre-wrap">{JSON.stringify(schema,null,2)}</pre></details>
   {operation&&(operation.startsWith('download/')||operation.startsWith('framework/artifact/')||operation.startsWith('framework/result/')||operation==='checkpoint')?<a className="text-sm text-blue-700" href={apiUrl(operation,payload)} download>파일 다운로드</a>:<Button tone="primary" busy={!!operation&&pending.has(operation)} disabled={!command} onClick={()=>void run()}>{command?.methods.includes('POST')?'선택 API 실행':'선택 API 조회'}</Button>}
   <ErrorMessage message={error}/>{result!==undefined&&<pre className="mt-3 max-h-96 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(result,null,2)}</pre>}
  </Panel>}
  {tab==='modules'&&<ModuleCatalog onRun={module=>{location.hash=(module.startsWith('FinRL-X:')?'finrl-trading':module.startsWith('FinRL:')?'frameworks':'project-modules')+'?module='+encodeURIComponent(module)}}/>}
 </div>;
}
