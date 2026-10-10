import {useState} from 'react';
import {Link2,RefreshCw} from 'lucide-react';
import {useEndpoint} from '../data/useEndpoint';
import {useOperations} from '../data/Operations';
import type {Connections} from '../data/types';
import {Panel,KeyValues} from '../ui/Panel';
import {Button,ErrorMessage,Skeleton,Status,inputClass} from '../ui/Primitives';
import {Capability} from '../ui/Capability';
import {OperationsControls} from '../ui/OperationsControls';
interface Provider {provider:string;environment:string;saved:boolean;vault_error?:string;last_test?:{ok:boolean;message:string}}
interface Settings {risk:{fee:number;slippage:number};data:{poll_seconds:number;timeout_seconds:number};symbols:string[];expert_devices:Record<string,string>}
function ProviderForm(){
 const provider=useEndpoint<Provider>('provider'),{execute,pending}=useOperations();
 const [environment,setEnvironment]=useState('real'),[appKey,setAppKey]=useState(''),[secret,setSecret]=useState(''),[account,setAccount]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('');
 async function send(action:string){setError('');setMessage('');try{
  const result=await execute<{message?:string;last_test?:{message:string}}>('provider/'+action,{environment,app_key:appKey,secret,account});
  setMessage(result.message||result.last_test?.message||'연결 설정을 반영했습니다.');
  if(action==='connect'){setAppKey('');setSecret('');setAccount('');}await provider.refresh();
 }catch(e){setError(e instanceof Error?e.message:String(e));}}
 return <Panel title="키움 인증·시세 연결" description="기존 OS 보안 저장소 사용 · 실제 주문 전송 기능은 연결하지 않습니다." actions={<Button busy={pending.has('provider/disconnect')} onClick={()=>void send('disconnect')}>시세 연결 해제</Button>}>
  <OperationsControls/>
  <KeyValues items={[["공급원",provider.data?.provider],["저장 환경",provider.data?.environment],["인증 저장",provider.data?.saved?'저장됨':'미저장']]}/>
  <ErrorMessage message={error||provider.error||provider.data?.vault_error||''}/>
  {provider.data?.last_test&&<p className="my-3 text-xs text-slate-500">{provider.data.last_test.message}</p>}
  <div className="mt-4 space-y-3"><label className="block text-xs text-slate-500">키 발급 환경<select className={inputClass+' mt-2'} value={environment} onChange={e=>setEnvironment(e.target.value)}><option value="real">실전 시세</option><option value="paper">모의투자 시세</option></select></label>
  <input aria-label="App Key" type="password" autoComplete="off" className={inputClass} placeholder="App Key" value={appKey} onChange={e=>setAppKey(e.target.value)}/>
  <input aria-label="Secret Key" type="password" autoComplete="off" className={inputClass} placeholder="Secret Key" value={secret} onChange={e=>setSecret(e.target.value)}/>
  <input aria-label="계좌 정보" type="password" autoComplete="off" className={inputClass} placeholder="계좌 정보 (선택)" value={account} onChange={e=>setAccount(e.target.value)}/>
  <div className="flex flex-wrap gap-2"><Button tone="primary" busy={pending.has('provider/connect')} onClick={()=>void send('connect')}>인증 후 저장·선택</Button><Button busy={pending.has('provider/test')} onClick={()=>void send('test')}>저장된 키 인증 확인</Button><Button busy={pending.has('provider/public')} onClick={()=>void send('public')}>공개 시세 선택</Button></div>{message&&<p className="text-xs text-slate-600">{message}</p>}</div>
 </Panel>;
}
function OperationalSettings(){
 const endpoint=useEndpoint<Settings>('settings'),{execute,pending}=useOperations();const [draft,setDraft]=useState<Settings|null>(null),[error,setError]=useState(''),[message,setMessage]=useState('');
 const value=draft||endpoint.data;
 async function save(){if(!value)return;setError('');try{const {risk,data,symbols,expert_devices}=value;await execute('settings',{risk,data,symbols,expert_devices});setMessage('운영 설정을 저장했습니다.');await endpoint.refresh();setDraft(null);}catch(e){setError(e instanceof Error?e.message:String(e));}}
 return <Panel title="운영 설정" description="기존 시세·가상계좌·Expert 장치 설정 · SAC 원본 학습값은 읽기 전용입니다."><ErrorMessage message={error||endpoint.error}/>{value&&<div className="space-y-4">
  {(['fee','slippage'] as const).map(key=><label key={key} className="block text-xs text-slate-500">{key==='fee'?'가상매매 수수료율':'가상매매 슬리피지율'}<input type="number" step="any" className={inputClass+' mt-2'} value={value.risk[key]} onChange={e=>setDraft({...value,risk:{...value.risk,[key]:Number(e.target.value)}})}/></label>)}
  {(['poll_seconds','timeout_seconds'] as const).map(key=><label key={key} className="block text-xs text-slate-500">{key==='poll_seconds'?'시세 폴링 주기(초)':'시세 요청 대기(초)'}<input type="number" step="any" className={inputClass+' mt-2'} value={value.data[key]} onChange={e=>setDraft({...value,data:{...value.data,[key]:Number(e.target.value)}})}/></label>)}
  <label className="block text-xs text-slate-500">수신 종목 (쉼표 구분 · 비우면 기존 전체 목록)<input className={inputClass+' mt-2'} value={value.symbols.join(', ')} onChange={e=>setDraft({...value,symbols:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})}/></label>
  <label className="block text-xs text-slate-500">Expert별 장치 (JSON)<textarea className={inputClass+' mt-2'} defaultValue={JSON.stringify(value.expert_devices,null,2)} onBlur={e=>{try{setDraft({...value,expert_devices:JSON.parse(e.target.value)});setError('');}catch{setError('장치 설정 JSON을 확인하세요.');}}}/></label>
  <Button tone="primary" disabled={!!error} busy={pending.has('settings')} onClick={()=>void save()}>운영 설정 저장</Button>{message&&<p className="text-xs text-slate-500">{message}</p>}
 </div>}</Panel>;
}
export function ConnectionSettings(){const {state:s}=useOperations();const connection=useEndpoint<Connections>('connections');if(!s)return <Skeleton/>;
 return <div className="grid items-start gap-6 lg:grid-cols-2"><div className="space-y-6"><Panel title="연결 상태" description="현재 API·원격 데이터 공급원 · 인증 값은 응답에 포함하지 않습니다." actions={<Button busy={connection.loading} onClick={()=>void connection.refresh()}><RefreshCw size={14}/>연결 확인</Button>}><ErrorMessage message={connection.error}/><div className="flex items-center gap-2 text-sm font-bold"><Link2 size={17} className="text-blue-500"/>로컬 SAC API <Status tone={connection.data?'good':'idle'}>{connection.data?'응답 확인':'확인 중'}</Status></div><KeyValues items={[["API 주소",new URL('/api',location.origin).href],["현재 가격 DB",s.data.path],["원격 공급원",connection.data?.data.source||'미설정'],["원격 상태",connection.data?.data.status]]}/><p className="mt-4 text-xs text-slate-500">FMP는 기존 FinRL-X 설정 모듈에서 인증을 읽습니다.</p></Panel><ProviderForm/></div>
 <div className="space-y-6"><Panel title="증권사 연결" description="현재 실행 경로의 연결 상태"><div className="space-y-4"><Capability name="kiwoom" label="키움 시세 연결"/><Capability name="alpaca" label="Alpaca 주문 연결"/><Capability name="live_feed" label="실시간 입력"/></div></Panel><OperationalSettings/><Panel title="학습 설정 출처"><KeyValues items={[["학습 설정",s.settings.parameter_source],["환경 설정",s.settings.environment_source],["실행 단계",s.settings.steps_per_run]]}/></Panel></div></div>;
}
