import {Search,Cpu} from 'lucide-react';
import {useState} from 'react';
import {Input,Select} from '@platform/ui/Primitives';
export interface LocalModel {path:string;name:string;bytes:number}
export function LocalModelPicker({files,selected,onChange,disabled}:{files:LocalModel[];selected:string;onChange:(value:string)=>void;disabled:boolean}) {
  const [query,setQuery]=useState('');
  const visible=files.filter(file=>(file.name+' '+file.path).toLowerCase().includes(query.trim().toLowerCase()));
  const chosen=files.find(file=>file.path===selected);
  return <div className="agent-model-picker">
    {files.length>1&&<div className="ui-search-field"><Search size={16}/><Input aria-label="로컬 모델 검색" placeholder="모델 이름으로 찾기" value={query} onChange={event=>setQuery(event.target.value)}/></div>}
    <label>사용할 모델<Select aria-label="로컬 모델 선택" disabled={disabled||!files.length} value={selected} onChange={event=>onChange(event.target.value)}>
      {!files.length&&<option value="">모델 폴더에 GGUF 파일을 넣어 주세요</option>}
      {selected&&!visible.some(file=>file.path===selected)&&<option value={selected}>{chosen?.name||selected} · 선택됨</option>}
      {visible.map(file=><option key={file.path} value={file.path}>{file.name} · {(file.bytes/1048576).toFixed(0)} MB</option>)}
    </Select></label>
    {query&&<p className="ui-field-hint" role="status">검색 결과 {visible.length}개 · 선택한 모델은 유지됩니다.</p>}
    {chosen&&<div className="agent-selected-model"><Cpu size={21}/><div><strong>{chosen.name.replace(/\.gguf$/i,'')}</strong><span>{(chosen.bytes/1048576).toFixed(0)} MB · GPU 우선 실행</span><small title={chosen.path}>{chosen.path}</small></div></div>}
  </div>;
}
