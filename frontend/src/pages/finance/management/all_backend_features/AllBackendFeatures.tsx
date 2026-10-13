import {useEffect,useState} from 'react';
import {useOperations,useSystemState} from '../../../../data/Operations';
import {apiUrl} from '../../../../data/api';
import type {BackendMenuCatalog,JsonSchema} from '../../../../data/menu_types';
import {NativeModuleRunner} from '../../../shared/frameworks/NativeModuleRunner';
import {ModuleCatalog} from '../../../shared/frameworks/FrameworkWorkspace';
import {Panel} from '../../../../ui/Panel';
import {Button,ErrorMessage,Tabs,inputClass} from '../../../../ui/Primitives';

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

export function AllBackendFeatures(){
 const catalog=useSystemState<BackendMenuCatalog>('menu_catalog'),{execute,pending}=useOperations();
 const selection=new URLSearchParams(location.hash.split('?')[1]??'');
 const [tab,setTab]=useState(selection.get('tab')??'features'),[groupId,setGroupId]=useState(selection.get('group')??''),[menuId,setMenuId]=useState(''),[query,setQuery]=useState(''),[commandKey,setCommandKey]=useState(''),[paths,setPaths]=useState<Record<string,unknown>>({}),[payload,setPayload]=useState<Record<string,unknown>>({}),[raw,setRaw]=useState('{}'),[error,setError]=useState(''),[result,setResult]=useState<unknown>();
 const [selectedModule,setSelectedModule]=useState('');
 const groups=catalog.data?.groups??[],menus=groups.filter(group=>!groupId||group.id===groupId).flatMap(group=>group.menus);
 const commands=(catalog.data?.commands??[]).filter(item=>(!groupId||item.group===groupId)&&(!menuId||item.menu===menuId)&&(!query||(item.operation+' '+item.function+' '+item.description).toLowerCase().includes(query.toLowerCase()))),command=commands.find(item=>item.operation+'|'+item.methods.join(',')===commandKey)??commands[0];
 const operation=command?.operation.replace(/\{([^}:]+)(?::[^}]+)?\}/g,(_,key:string)=>String(paths[key]??''));
 const schema=command?.methods.includes('POST')?command.body_schema:command?.query_schema;
 const structured=!!Object.keys(schema?.properties??{}).length;
 useEffect(()=>{setPaths({});setPayload({});setRaw('{}');setError('');setResult(undefined)},[command?.operation,command?.methods.join(',')]);
 const run=async()=>{
  if(!command||!operation)return;setError('');setResult(undefined);
  try{
   for(const name of command.path_schema.required??[])if(paths[name]==null||paths[name]==='')throw new Error('경로 입력이 필요합니다: '+name);
   const extra=JSON.parse(raw);
   if(extra==null||typeof extra!=='object'||Array.isArray(extra))throw new Error('추가 입력은 JSON 객체여야 합니다.');
   const args=structured?{...(schema?.additionalProperties===true?extra:{}),...payload}:extra;
   if(args==null||typeof args!=='object'||Array.isArray(args))throw new Error('입력은 JSON 객체여야 합니다.');
   if(structured)for(const [name,property] of Object.entries(schema?.properties??{})){
    const type=(property.anyOf?.find(item=>item.type!=='null')??property).type;
    if(args[name]!=null&&typeof args[name]==='string'&&(type==='object'||type==='array'))args[name]=JSON.parse(args[name] as string);
    if(args[name]!=null&&(type==='number'||type==='integer')){const number=Number(args[name]);if(!Number.isFinite(number))throw new Error(name+': 숫자를 입력하세요.');args[name]=number;}
   }
   setResult(await execute(operation,args,command.methods.includes('POST')?'POST':'GET'));
  }catch(e){setError(e instanceof Error?e.message:'실행 실패')}
 };
 return <div className="space-y-3">
  <Panel title="백엔드 기능 전체" description="등록된 기능·API·원본 모듈을 확인하고 필요한 항목을 선택합니다. 목록에서 임의로 기능을 제거하지 않습니다.">
   <ErrorMessage message={catalog.error}/>
   <Tabs value={tab} onChange={setTab} items={[{id:'features',label:'큰 메뉴 · 전체 기능'},{id:'commands',label:'등록된 API · 입력값'},{id:'modules',label:'원본 모듈 · 함수'}]}/>
   <div className="mt-3 flex flex-wrap gap-2"><select className={inputClass} aria-label="큰 메뉴 선택" value={groupId} onChange={e=>{setGroupId(e.target.value);setMenuId('');setCommandKey('');setPaths({});setPayload({});setRaw('{}');setResult(undefined)}}><option value="">큰 메뉴 전체</option>{groups.map(group=><option key={group.id} value={group.id}>{group.title}</option>)}</select><select className={inputClass} aria-label="작은 메뉴 선택" value={menuId} onChange={e=>{setMenuId(e.target.value);setCommandKey('');setPaths({});setPayload({});setRaw('{}');setResult(undefined)}}><option value="">작은 메뉴 전체</option>{menus.map(menu=><option key={menu.id} value={menu.id}>{menu.title}</option>)}</select></div>
   <input className={inputClass+' mt-3 max-w-md'} value={query} onChange={e=>setQuery(e.target.value)} placeholder="기능·메뉴·모듈·API 검색" aria-label="백엔드 기능 검색"/>
  </Panel>
  {tab==='features'&&groups.filter(group=>!groupId||group.id===groupId).map(group=>{
   const actions=catalog.data?.actions.filter(item=>item.group===group.id&&(!menuId||item.menu_id===menuId)&&(!query||(item.name+' '+item.module+' '+item.function).toLowerCase().includes(query.toLowerCase())))??[];
   const menus=group.menus.filter(item=>(!menuId||item.id===menuId)&&(!query||(item.title+' '+item.operations.join(' ')).toLowerCase().includes(query.toLowerCase())));
   if(!menus.length&&!actions.length)return null;
   return <Panel key={group.id} title={group.title} description={'기존 화면 '+group.menus.length+'개 · 등록된 추가 작업 '+(catalog.data?.actions.filter(item=>item.group===group.id).length??0)+'개'}>
    <div className="grid gap-2 sm:grid-cols-2">{menus.map(menu=><div className="rounded border border-slate-200 p-2 text-xs" key={menu.id}><a className="text-blue-700" href={'#'+menu.id}><b>{menu.title}</b></a><span className="mt-1 block text-slate-500">화면: {menu.frontend}</span><span className="block text-slate-500">매니저: {menu.manager}</span><button className="mt-2 text-blue-700" onClick={()=>{setGroupId(group.id);setMenuId(menu.id);setCommandKey('');setPaths({});setPayload({});setRaw('{}');setError('');setResult(undefined);setTab('commands')}}>소속 API · 입력값 보기</button></div>)}</div>
    <div className="mt-3 overflow-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b text-slate-500"><th>추가 기능 · 작은 메뉴</th><th>원본·함수</th><th>입력 항목</th><th>연결</th></tr></thead><tbody>{actions.map(item=><tr className="border-b border-slate-100" key={item.id}><td className="p-2">{item.name}<span className="block text-slate-500">{group.menus.find(menu=>menu.id===item.menu_id)?.title}</span></td><td className="p-2 break-all">{item.module}<br/>{item.function}</td><td className="p-2">{item.fields.join(', ')||'입력 없음'}</td><td className="p-2">{item.id==='native_call'?<><a className="block text-blue-700" href="#finance/modules_tools">FinRL 원본 함수</a><button className="block text-blue-700" onClick={()=>setTab('modules')}>원본 모듈 선택</button></>:<a className="text-blue-700" href={'#'+item.menu_id+'/'+item.id}>기능 열기</a>}</td></tr>)}</tbody></table></div>
   </Panel>;
  })}
  {tab==='commands'&&<Panel title="등록된 API · 전체 입력값" description="기존 단일 API를 사용합니다. 입력을 비우면 해당 API의 원본 기본값을 사용합니다.">
   <select className={inputClass} value={command?command.operation+'|'+command.methods.join(','):''} onChange={e=>{setCommandKey(e.target.value);setPaths({});setPayload({});setRaw('{}');setError('');setResult(undefined)}} aria-label="API 선택">{commands.filter(item=>!query||(item.operation+' '+item.function).toLowerCase().includes(query.toLowerCase())).map(item=><option key={item.operation+'|'+item.methods.join(',')} value={item.operation+'|'+item.methods.join(',')}>{item.operation} · {item.methods.join(', ')}</option>)}</select>
   <p className="my-2 break-all text-xs text-slate-500">{command?.module} · {command?.function} · {groups.find(group=>group.id===command?.group)?.title} → {menus.find(menu=>menu.id===command?.menu)?.title}</p>
   {command?.description&&<details className="mb-3 text-xs text-slate-500"><summary>원본 설명</summary><p className="mt-2 whitespace-pre-wrap">{command.description}</p></details>}
   {command&&<div className="mb-3 grid gap-3 sm:grid-cols-2">{fields(command.path_schema,paths,setPaths)}</div>}
   {schema&&structured?<div className="mb-3 grid gap-3 sm:grid-cols-2">{fields(schema,payload,setPayload)}</div>:<label className="block text-xs text-slate-600">전체 입력 JSON<textarea className={inputClass+' my-2 min-h-24 font-mono'} value={raw} onChange={e=>setRaw(e.target.value)}/></label>}
   {structured&&schema?.additionalProperties===true&&<details className="my-3 text-xs text-slate-600"><summary>추가 입력 JSON</summary><textarea aria-label="추가 API 입력" className={inputClass+' my-2 min-h-24 font-mono'} value={raw} onChange={e=>setRaw(e.target.value)}/></details>}
   <details className="my-3 text-xs text-slate-500"><summary>전체 입력 계약</summary><pre className="mt-2 overflow-auto whitespace-pre-wrap">{JSON.stringify(schema,null,2)}</pre></details>
   {operation&&(operation.startsWith('download/')||operation.startsWith('framework/artifact/')||operation.startsWith('framework/result/')||operation==='checkpoint')?<a className="text-sm text-blue-700" href={apiUrl(operation,payload)} download>파일 다운로드</a>:<Button tone="primary" busy={!!operation&&pending.has(operation)} disabled={!command} onClick={()=>void run()}>{command?.methods.includes('POST')?'선택 API 실행':'선택 API 조회'}</Button>}
   <ErrorMessage message={error}/>{result!==undefined&&<pre className="mt-3 max-h-96 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(result,null,2)}</pre>}
  </Panel>}
  {tab==='modules'&&<><ModuleCatalog onRun={setSelectedModule}/><NativeModuleRunner selectedModule={selectedModule} onSelect={setSelectedModule}/></>}
 </div>;
}
