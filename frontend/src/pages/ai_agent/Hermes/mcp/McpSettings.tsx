import {useEffect,useState} from 'react';
import {request} from '../../../../data/api';
import {Button,ErrorMessage} from '../../../../ui/Primitives';
import {prefix,failure} from '../types';
interface McpState {servers:Record<string,unknown>;status:Record<string,unknown>[]}
export function McpSettings({busy}:{busy:boolean}){
 const [text,setText]=useState('{}'),[rows,setRows]=useState<Record<string,unknown>[]>([]),[error,setError]=useState(''),[notice,setNotice]=useState(''),[pending,setPending]=useState('');
 const accept=(state:McpState)=>{setText(JSON.stringify(state.servers,null,2));setRows(state.status)};
 useEffect(()=>{let live=true;void request<McpState>(prefix+'mcp',{},'GET').then(v=>{if(live)accept(v)}).catch(e=>{if(live)setError(failure(e))});return()=>{live=false}},[]);
 const run=async(mode:'save'|'connect')=>{setPending(mode);setError('');setNotice('');try{const body=mode==='save'?{servers:JSON.parse(text)}:{};const state=await request<McpState>(prefix+'mcp/'+mode,body);accept(state);setNotice(mode==='save'?'MCP 설정을 저장했습니다. 연결 버튼으로 도구를 불러오세요.':'연결 결과를 갱신했습니다.')}catch(e){setError(failure(e))}finally{setPending('')}};
 return <section className="hermes-settings"><h3>MCP 서버</h3><p className="hermes-muted">연결한 MCP 서버의 도구를 Hermes가 사용할 수 있습니다.</p><label>서버 설정<textarea aria-label="MCP 서버 JSON 설정" className="hermes-code-editor" rows={12} spellCheck={false} value={text} disabled={busy||!!pending} onChange={e=>setText(e.target.value)}/></label><details><summary>설정 예시</summary><pre>{JSON.stringify({local:{command:'실행파일 경로',args:['서버 스크립트 경로']},remote:{url:'https://서버주소/mcp'}},null,2)}</pre></details><div className="hermes-actions"><Button tone="primary" disabled={busy||!!pending} busy={pending==='save'} onClick={()=>void run('save')}>설정 저장</Button><Button disabled={busy||!!pending} busy={pending==='connect'} onClick={()=>void run('connect')}>연결·도구 불러오기</Button></div><ErrorMessage message={error}/>{notice&&<p role="status" className="hermes-notice">{notice}</p>}<div className="hermes-mcp-results">{rows.map((row,i)=><details key={i}><summary>{String(row.name??row.server??'MCP 서버')} · {String(row.status??row.state??(row.connected?'연결됨':'연결 확인 필요'))}</summary><pre>{JSON.stringify(row,null,2)}</pre></details>)}{!rows.length&&<p className="hermes-muted">등록된 MCP 서버가 없습니다.</p>}</div></section>;
}
