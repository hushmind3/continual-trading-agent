import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Textarea,Select,ErrorMessage} from '@platform/ui/Primitives';
import {Panel} from '@platform/ui/Panel';
import {useKorean} from './useKorean';
interface Tool {name:string;description?:string;inputSchema?:unknown}
export function McpTools({projectId}:{projectId:string}){
 const [tools,setTools]=useState<Tool[]>([]),[name,setName]=useState(''),[args,setArgs]=useState('{}'),[output,setOutput]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function load(){setBusy(true);setError('');try{const data=await request<{tools:Tool[]}>('projects/invoke',{id:projectId,operation:'list'},'POST',80000);setTools(data.tools);setName(previous=>previous||data.tools[0]?.name||'')}catch(e){setError(String(e))}finally{setBusy(false)}}
 useEffect(()=>{void load()},[projectId]);
 async function run(){setBusy(true);setError('');try{const arguments_=JSON.parse(args);if(!arguments_||Array.isArray(arguments_)||typeof arguments_!=='object')throw Error('실행 인수는 JSON 객체로 입력하세요.');const result=await request<unknown>('projects/invoke',{id:projectId,operation:'call',name,arguments:arguments_},'POST',80000);setOutput(JSON.stringify(result,null,2))}catch(e){setError(String(e))}finally{setBusy(false)}}
 const selected=tools.find(tool=>tool.name===name);
 const language=useKorean([selected?.description||''],localStorage.getItem('projects.korean')!=='false');
 return <div className="min-h-0 flex-1 overflow-auto p-4"><Panel title={'연결된 MCP 도구 · '+tools.length+'개'} actions={<Button busy={busy} onClick={()=>void load()}>다시 연결</Button>}><ErrorMessage message={error}/><div className="space-y-4"><Select aria-label="MCP 도구" value={name} onChange={e=>{setName(e.target.value);setArgs('{}')}}>{tools.map(tool=><option key={tool.name} value={tool.name}>{tool.name}</option>)}</Select><p className="whitespace-pre-wrap text-sm text-slate-600">{language.text(selected?.description||'')}</p><details><summary className="cursor-pointer text-sm">입력 항목 보기</summary><pre className="overflow-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(selected?.inputSchema,null,2)}</pre></details><Textarea aria-label="MCP 실행 인수" rows={5} value={args} onChange={e=>setArgs(e.target.value)} placeholder='{"path":"C:/..."}'/><Button tone="primary" disabled={!name} busy={busy} onClick={()=>void run()}>도구 실행</Button><pre className="whitespace-pre-wrap break-words text-sm">{output}</pre></div></Panel></div>;
}
