import {FrameworkProviders} from './FrameworkProviders';
import {useState} from 'react';
import {Link2,RefreshCw} from 'lucide-react';
import {useSystemState,useOperations} from '../../../../data/Operations';
import type {Connections} from '../../../../data/types';
import {Panel,KeyValues} from '../../../../ui/Panel';
import {Button,ErrorMessage,Skeleton,Status,inputClass} from '../../../../ui/Primitives';
import {Capability} from '../../../../ui/Capability';
interface Provider {provider:string;environment:string;saved:boolean;vault_error?:string;last_test?:{ok:boolean;message:string}}
interface Settings {risk:{fee:number;slippage:number};data:{poll_seconds:number;timeout_seconds:number};symbols:string[];expert_devices:Record<string,string>}
function ProviderForm(){
 const provider=useSystemState<Provider>('provider'),{execute,pending}=useOperations();
 const [environment,setEnvironment]=useState('real'),[appKey,setAppKey]=useState(''),[secret,setSecret]=useState(''),[account,setAccount]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('');
 async function send(action:string){setError('');setMessage('');try{
  const result=await execute<{message?:string;last_test?:{message:string}}>('provider/'+action,{environment,app_key:appKey,secret,account});
  setMessage(result.message||result.last_test?.message||'연결 설정을 반영했습니다.');
  if(action==='connect'){setAppKey('');setSecret('');setAccount('');}
 }catch(e){setError(e instanceof Error?e.message:String(e));}}
 return <Panel title="키움 인증" className="connection-provider" description="인증은 OS 보안 저장소에 보관하며 실제 주문을 전송하지 않습니다." actions={<Button busy={pending.has('provider/disconnect')} onClick={()=>void send('disconnect')}>시세 연결 해제</Button>}>

  <div className="connection-provider-status"><Status tone={provider.data?.saved?'good':'idle'}>{provider.data?provider.data.saved?'인증 저장됨':'인증 설정 필요':'인증 상태 조회 중'}</Status><span>{provider.data?.provider==='kiwoom'?'키움':provider.data?.provider??'—'} · {provider.data?.environment==='real'?'실전':provider.data?.environment==='paper'?'모의':provider.data?.environment??'—'}</span></div>
  <ErrorMessage message={error||provider.error||provider.data?.vault_error||''}/>
  {provider.data?.last_test&&<p className="my-3 text-xs text-slate-500">{provider.data.last_test.message}</p>}
  <div className="connection-provider-fields"><label className="block text-xs text-slate-500">키 발급 환경<select className={inputClass+' mt-2'} value={environment} onChange={e=>setEnvironment(e.target.value)}><option value="real">실전 시세</option><option value="paper">모의투자 시세</option></select></label>
  <div className="connection-key-grid"><label>App Key<input aria-label="App Key" type="password" autoComplete="off" className={inputClass} placeholder="발급받은 App Key" value={appKey} onChange={e=>setAppKey(e.target.value)}/></label>
  <label>Secret Key<input aria-label="Secret Key" type="password" autoComplete="off" className={inputClass} placeholder="발급받은 Secret Key" value={secret} onChange={e=>setSecret(e.target.value)}/></label></div>
  <label className="block text-xs text-slate-500">계좌 정보 · 선택<input aria-label="계좌 정보" type="password" autoComplete="off" className={inputClass+' mt-2'} placeholder="필요한 경우에만 입력" value={account} onChange={e=>setAccount(e.target.value)}/></label>
  <div className="connection-auth-actions"><Button tone="primary" busy={pending.has('provider/connect')} onClick={()=>void send('connect')}>인증 후 저장·선택</Button><Button busy={pending.has('provider/test')} onClick={()=>void send('test')}>저장된 키 인증 확인</Button><details className="connection-public-choice"><summary>다른 시세 연결</summary><Button busy={pending.has('provider/public')} onClick={()=>void send('public')}>공개 시세 선택</Button></details></div>{message&&<p className="text-xs text-slate-600">{message}</p>}</div>
 </Panel>;
}
function OperationalSettings(){
 const endpoint=useSystemState<Settings>('settings'),{execute,pending}=useOperations();const [draft,setDraft]=useState<Settings|null>(null),[error,setError]=useState(''),[message,setMessage]=useState(''),[deviceJsonError,setDeviceJsonError]=useState('');
 const value=draft||endpoint.data;
 async function save(){if(!value||deviceJsonError)return;setError('');setMessage('');try{const {risk,data,symbols,expert_devices}=value;await execute('settings',{risk,data,symbols,expert_devices});setMessage('운영 설정을 저장했습니다.');setDraft(null);}catch(e){setError(e instanceof Error?e.message:String(e));}}
 return <Panel title="운영 설정" className="connection-operational-settings" description="시세 수신·가상매매·Expert 장치를 설정합니다. 알고리즘 기본값은 변경하지 않습니다."><ErrorMessage message={deviceJsonError||error||endpoint.error}/>{value&&<div className="space-y-4">
  <div className="connection-setting-grid">{(['fee','slippage'] as const).map(key=><label key={key} className="block text-xs text-slate-500">{key==='fee'?'수수료 (%)':'슬리피지 (%)'}<input type="number" step="any" className={inputClass+' mt-2'} value={value.risk[key]*100} onChange={e=>setDraft({...value,risk:{...value.risk,[key]:Number(e.target.value)/100}})}/></label>)}
  {(['poll_seconds','timeout_seconds'] as const).map(key=><label key={key} className="block text-xs text-slate-500">{key==='poll_seconds'?'시세 폴링 주기(초)':'시세 요청 대기(초)'}<input type="number" step="any" className={inputClass+' mt-2'} value={value.data[key]} onChange={e=>setDraft({...value,data:{...value.data,[key]:Number(e.target.value)}})}/></label>)}
  </div><label className="block text-xs text-slate-500">수신 종목 (쉼표 구분 · 비우면 기존 전체 목록)<input className={inputClass+' mt-2'} value={value.symbols.join(', ')} onChange={e=>setDraft({...value,symbols:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})}/></label>
  <details className="connection-device-settings"><summary>Expert별 실행 장치</summary><label className="mt-3 block text-xs text-slate-500">장치 설정 (JSON)<textarea className={inputClass+' mt-2'} defaultValue={JSON.stringify(value.expert_devices,null,2)} onChange={e=>{try{setDraft({...value,expert_devices:JSON.parse(e.target.value)});setDeviceJsonError('');}catch{setDeviceJsonError('장치 설정 JSON을 확인하세요.');}}}/></label></details>
  <div className="connection-save-row"><Status tone={deviceJsonError?'warn':draft?'warn':'idle'}>{deviceJsonError?'입력 확인 필요':draft?'저장하지 않은 변경':'현재 저장된 설정'}</Status><Button tone="primary" disabled={!!deviceJsonError} busy={pending.has('settings')} onClick={()=>void save()}>운영 설정 저장</Button>{message&&<p className="text-xs text-slate-500">{message}</p>}</div>
 </div>}</Panel>;
}
export function ConnectionSettings(){const {state:s}=useOperations();const connection=useSystemState<Connections>('connections');if(!s)return <Skeleton/>;
 return <div className="connection-workspace space-y-6"><Panel title="연결 상태" description="로컬 API와 데이터 공급원의 현재 상태입니다." className="connection-status" actions={<Button busy={connection.loading} onClick={()=>void connection.refresh()}><RefreshCw size={14}/>연결 확인</Button>}>
 <ErrorMessage message={connection.error}/><div className="connection-api-state"><span><Link2 size={17}/>로컬 API</span><Status tone={connection.error?'bad':connection.data?'good':'idle'}>{connection.error?'조회 오류':connection.data?'응답 확인':'확인 중'}</Status></div><KeyValues items={[["API 주소",new URL('/api',location.origin).href],["현재 가격 DB",s.data.path],["추가 데이터 공급원",connection.data?.data.source||'미설정'],["공급원 상태",connection.data?.data.status]]}/></Panel>
 <div className="connection-config-grid"><ProviderForm/><OperationalSettings/></div>
 <div className="connection-secondary-grid"><Panel title="연결 기능" description="현재 실행 경로의 지원 상태"><div className="space-y-4"><Capability name="kiwoom" label="키움 시세 연결"/><Capability name="live_feed" label="실시간 입력"/></div></Panel><details className="workspace-disclosure"><summary>학습 설정 출처</summary><KeyValues items={[["학습 설정",s.settings.parameter_source],["환경 설정",s.settings.environment_source],["실행 단계",s.settings.steps_per_run]]}/></details></div>
 <details className="workspace-disclosure connection-extra-providers"><summary>추가 시세·데이터 공급원</summary><p className="my-3 text-xs leading-6 text-slate-500">FMP는 금융 백엔드의 공급원 인증 저장소에서 설정을 읽습니다.</p><FrameworkProviders/></details>
 </div>;
}
