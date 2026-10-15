import {FrameworkProviders} from './FrameworkProviders';
import {useState} from 'react';
import {Link2,RefreshCw} from 'lucide-react';
import {useSystemState,useOperations} from '../../../../data/Operations';
import type {Connections} from '../../../../data/types';
import {Panel,KeyValues} from '../../../../ui/Panel';
import {Button,ErrorMessage,Skeleton,Status,inputClass} from '../../../../ui/Primitives';
const providerStatusNames:Record<string,string>={requires_configuration:'설정 필요',not_configured:'미설정',configured:'설정됨',unknown:'미확인',error:'오류'};
interface Provider {provider:string;environment:string;saved:boolean;vault_error?:string;last_test?:{ok:boolean;message:string}}
interface Settings {risk:{fee:number;slippage:number};data:{poll_seconds:number;timeout_seconds:number};symbols:string[];expert_devices:Record<string,string>}
function ProviderForm(){
 const provider=useSystemState<Provider>('provider'),{execute,pending}=useOperations();
 const [environment,setEnvironment]=useState('real'),[appKey,setAppKey]=useState(''),[secret,setSecret]=useState(''),[account,setAccount]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('');
 const providerBusy=['connect','test','disconnect','public'].some(action=>pending.has('provider/'+action));
 const missingKeys=!provider.data?.saved&&(!appKey.trim()||!secret.trim());
 async function send(action:string){if(providerBusy||(action==='connect'&&missingKeys))return;setError('');setMessage('');try{
  const result=await execute<{message?:string;last_test?:{message:string}}>('provider/'+action,{environment,app_key:appKey,secret,account});
  setMessage(result.message||result.last_test?.message||'연결 설정을 반영했습니다.');
  if(action==='connect'){setAppKey('');setSecret('');setAccount('');}
 }catch(e){setError(e instanceof Error?e.message:String(e));}}
 return <Panel title="키움 인증" className="connection-provider" description="인증은 OS 보안 저장소에 보관하며 실제 주문을 전송하지 않습니다." actions={<Button disabled={providerBusy} busy={pending.has('provider/disconnect')} onClick={()=>void send('disconnect')}>시세 연결 해제</Button>}>

  <div className="connection-provider-status"><Status tone={provider.data?.saved?'good':'idle'}>{provider.data?provider.data.saved?'인증 저장됨':'인증 설정 필요':'인증 상태 조회 중'}</Status><span>{provider.data?.provider==='kiwoom'?'키움':provider.data?.provider??'—'} · {provider.data?.environment==='real'?'실전':provider.data?.environment==='paper'?'모의':provider.data?.environment??'—'}</span></div>
  <ErrorMessage message={error||provider.error||provider.data?.vault_error||''}/>
  {provider.data?.last_test&&<p className="my-3 text-xs text-slate-500">{provider.data.last_test.message}</p>}
  <form onSubmit={event=>{event.preventDefault();void send('connect')}}><fieldset disabled={providerBusy} className="connection-provider-fields m-0 min-w-0 border-0 p-0"><legend className="sr-only">키움 인증 입력</legend><label className="block text-xs text-slate-500">키 발급 환경<select className={inputClass+' mt-2'} value={environment} onChange={e=>setEnvironment(e.target.value)}><option value="real">실전 시세</option><option value="paper">모의투자 시세</option></select></label>
  <div className="connection-key-grid"><label>App Key<input aria-label="App Key" type="password" autoComplete="off" className={inputClass} placeholder="발급받은 App Key" value={appKey} onChange={e=>setAppKey(e.target.value)}/></label>
  <label>Secret Key<input aria-label="Secret Key" type="password" autoComplete="off" className={inputClass} placeholder="발급받은 Secret Key" value={secret} onChange={e=>setSecret(e.target.value)}/></label></div>
  <label className="block text-xs text-slate-500">계좌 정보 · 선택<input aria-label="계좌 정보" type="password" autoComplete="off" className={inputClass+' mt-2'} placeholder="필요한 경우에만 입력" value={account} onChange={e=>setAccount(e.target.value)}/></label>
  <div className="connection-auth-actions"><Button type="submit" tone="primary" disabled={providerBusy||missingKeys} busy={pending.has('provider/connect')}>인증 후 저장·선택</Button><Button disabled={providerBusy||!provider.data?.saved} busy={pending.has('provider/test')} onClick={()=>void send('test')}>저장된 키 인증 확인</Button><details className="connection-public-choice"><summary>다른 시세 연결</summary><Button disabled={providerBusy} busy={pending.has('provider/public')} onClick={()=>void send('public')}>공개 시세 선택</Button></details></div>{missingKeys&&<p className="text-xs leading-5 text-slate-500">새 인증을 저장하려면 App Key와 Secret Key를 모두 입력하세요.</p>}</fieldset>{providerBusy&&<p role="status" className="mt-3 text-xs text-blue-700">인증 요청을 처리하고 있습니다.</p>}{message&&<p role="status" className="mt-3 text-xs text-slate-600">{message}</p>}</form>
 </Panel>;
}
function OperationalSettings(){
 const endpoint=useSystemState<Settings>('settings'),{state,execute,pending}=useOperations();const [draft,setDraft]=useState<Settings|null>(null),[error,setError]=useState(''),[message,setMessage]=useState(''),[deviceJsonError,setDeviceJsonError]=useState(''),[deviceJson,setDeviceJson]=useState<string|null>(null);
 const [numericDraft,setNumericDraft]=useState<Partial<Record<'fee'|'slippage'|'poll_seconds'|'timeout_seconds',string>>>({});
 const receiving=!!state?.operations?.controls.feed;
 const value=draft||endpoint.data,saving=pending.has('settings'),changed=!!draft||deviceJson!==null;
 const numberIssues:Partial<Record<'fee'|'slippage'|'poll_seconds'|'timeout_seconds',string>>={};
 if(value){for(const key of ['fee','slippage'] as const)if(!Number.isFinite(value.risk[key])||value.risk[key]<0)numberIssues[key]='0 이상의 숫자로 입력하세요.';for(const key of ['poll_seconds','timeout_seconds'] as const)if(!Number.isFinite(value.data[key])||value.data[key]<=0)numberIssues[key]='0보다 큰 초 단위 숫자로 입력하세요.';}
 const invalidNumbers=Object.keys(numberIssues).length>0;
 const update=(next:Settings)=>{setDraft(next);setMessage('');setError('')};
 const reset=()=>{setDraft(null);setNumericDraft({});setDeviceJson(null);setDeviceJsonError('');setError('');setMessage('저장하지 않은 변경을 되돌렸습니다.')};
 async function save(){if(!value||deviceJsonError||invalidNumbers||receiving||saving||!changed)return;setError('');setMessage('');try{const {risk,data,symbols,expert_devices}=value;await execute('settings',{risk,data,symbols,expert_devices});setMessage('운영 설정을 저장했습니다.');setDraft(null);setNumericDraft({});setDeviceJson(null);}catch(e){setError(e instanceof Error?e.message:String(e));}}
 return <Panel title="운영 설정" className="connection-operational-settings" description="시세 수신·가상매매·Expert 장치를 설정합니다. 알고리즘 기본값은 변경하지 않습니다."><ErrorMessage message={deviceJsonError||error||endpoint.error}/>{!value&&!endpoint.error&&<div role="status" className="connection-settings-loading"><Skeleton/><span>운영 설정을 불러오는 중</span></div>}{value&&<div className="space-y-4">{receiving&&<p className="rounded-xl bg-amber-50 p-3 text-xs leading-6 text-amber-800">시세 수신 중에는 운영 설정을 변경할 수 없습니다. <a className="underline" href="#finance/operation_control">운영 제어에서 중지</a>한 뒤 변경하세요.</p>}
  <fieldset disabled={saving||receiving} className="m-0 min-w-0 border-0 p-0"><legend className="sr-only">운영 설정 입력</legend><div className="connection-setting-grid">{(['fee','slippage'] as const).map(key=>{const label=key==='fee'?'수수료 (%)':'슬리피지 (%)';return <label key={key} className="block text-xs text-slate-500">{label}<input aria-label={label} type="number" min={0} step="any" aria-invalid={!!numberIssues[key]} aria-describedby={numberIssues[key]?'setting-'+key+'-error':undefined} className={inputClass+' mt-2'} value={numericDraft[key]??value.risk[key]*100} onChange={e=>{const raw=e.target.value;setNumericDraft(current=>({...current,[key]:raw}));update({...value,risk:{...value.risk,[key]:raw.trim()?Number(raw)/100:NaN}})}}/>{numberIssues[key]&&<span id={'setting-'+key+'-error'} role="alert" className="mt-2 block text-xs text-rose-700">{numberIssues[key]}</span>}</label>})}
  {(['poll_seconds','timeout_seconds'] as const).map(key=>{const label=key==='poll_seconds'?'시세 폴링 주기(초)':'시세 요청 대기(초)';return <label key={key} className="block text-xs text-slate-500">{label}<input aria-label={label} type="number" min={0} step="any" aria-invalid={!!numberIssues[key]} aria-describedby={numberIssues[key]?'setting-'+key+'-error':undefined} className={inputClass+' mt-2'} value={numericDraft[key]??value.data[key]} onChange={e=>{const raw=e.target.value;setNumericDraft(current=>({...current,[key]:raw}));update({...value,data:{...value.data,[key]:raw.trim()?Number(raw):NaN}})}}/>{numberIssues[key]&&<span id={'setting-'+key+'-error'} role="alert" className="mt-2 block text-xs text-rose-700">{numberIssues[key]}</span>}</label>})}
  </div><label className="block text-xs text-slate-500">수신 종목 (쉼표 구분 · 비우면 기존 전체 목록)<input className={inputClass+' mt-2'} value={value.symbols.join(', ')} onChange={e=>update({...value,symbols:e.target.value.split(',').map(s=>s.trim()).filter(Boolean)})}/></label>
  <details className="connection-device-settings"><summary>Expert별 실행 장치</summary><label className="mt-3 block text-xs text-slate-500">장치 설정 (JSON)<textarea className={inputClass+' mt-2'} value={deviceJson??JSON.stringify(value.expert_devices,null,2)} aria-invalid={!!deviceJsonError} onChange={e=>{setDeviceJson(e.target.value);setMessage('');try{const parsed:unknown=JSON.parse(e.target.value);if(!parsed||typeof parsed!=='object'||Array.isArray(parsed)||Object.values(parsed).some(device=>typeof device!=='string'))throw new Error();update({...value,expert_devices:parsed as Record<string,string>});setDeviceJsonError('');}catch{setDeviceJsonError('장치 설정은 모델 이름과 장치 문자열을 짝지은 JSON 객체로 입력하세요. 예: {"모델ID":"cuda:0"}');}}}/></label></details>
  </fieldset><div className="connection-save-row"><Status tone={deviceJsonError||invalidNumbers||changed?'warn':'idle'}>{saving?'저장 중':deviceJsonError||invalidNumbers?'입력 확인 필요':changed?'저장하지 않은 변경':'현재 저장된 설정'}</Status><div className="connection-save-actions"><Button disabled={!changed||saving} onClick={reset}>변경 취소</Button><Button aria-label="운영 설정 저장" tone="primary" disabled={!!deviceJsonError||invalidNumbers||receiving||!changed} busy={saving} onClick={()=>void save()}>설정 저장</Button></div>{message&&<p role="status" className="text-xs text-slate-500">{message}</p>}</div>
 </div>}</Panel>;
}
export function ConnectionSettings(){const {state:s}=useOperations();const connection=useSystemState<Connections>('connections');if(!s)return <Skeleton/>;
 return <div className="connection-workspace space-y-6"><Panel title="연결 상태" description="로컬 API와 데이터 공급원의 현재 상태입니다." className="connection-status" actions={<Button busy={connection.loading} onClick={()=>void connection.refresh()}><RefreshCw size={14}/>연결 확인</Button>}>
 <ErrorMessage message={connection.error}/><div className="connection-api-state"><span><Link2 size={17}/>플랫폼 연결</span><Status tone={connection.error?'bad':connection.data?'good':'idle'}>{connection.error?'조회 오류':connection.data?'응답 확인':'확인 중'}</Status></div><details className="connection-technical-details"><summary>접속 정보</summary><KeyValues items={[["API 주소",new URL('/api',location.origin).href],["현재 가격 DB",s.data.path],["추가 데이터 공급원",connection.data?.data.source||'미설정'],["공급원 상태",providerStatusNames[connection.data?.data.status??'']??connection.data?.data.status??'미확인']]}/></details></Panel>
 <div className="connection-config-grid"><ProviderForm/><OperationalSettings/></div>
 <div className="connection-secondary-grid"><details className="workspace-disclosure"><summary>학습 설정 출처</summary><KeyValues items={[["학습 설정",s.settings.parameter_source],["환경 설정",s.settings.environment_source],["실행 단계",s.settings.steps_per_run]]}/></details></div>
 <details className="workspace-disclosure connection-extra-providers"><summary>추가 시세·데이터 공급원</summary><p className="my-3 text-xs leading-6 text-slate-500">FMP는 금융 백엔드의 공급원 인증 저장소에서 설정을 읽습니다.</p><FrameworkProviders/></details>
 </div>;
}
