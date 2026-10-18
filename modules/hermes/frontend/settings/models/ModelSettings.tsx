import {useEffect,useState} from 'react';
import {RefreshCw,ArrowRight,Cpu} from 'lucide-react';
import {request} from '@platform/data/api';
import {Button,ErrorMessage,Tabs,Input,Status} from '@platform/ui/Primitives';
import {SettingsSection,SettingsLoadState} from '@platform/ui/SettingsSection';
import {prefix,failure,type Settings,type AgentStatus} from '../../types';
import {useAgentSettings} from '../useAgentSettings';
import {LocalModelPicker,type LocalModel} from './LocalModelPicker';
import {ModelServerForm} from './ModelServerForm';
import {ModelRuntimeControls} from './ModelRuntimeControls';
export function ModelSettings({busy,onStatus,localModel,onChat}:{busy:boolean;onStatus:(status:AgentStatus)=>void;localModel?:AgentStatus['local_model'];onChat:()=>void}) {
 const {cfg,setCfg,acceptCfg,error,setError,reload}=useAgentSettings();
 const [files,setFiles]=useState<LocalModel[]>([]),[models,setModels]=useState<string[]>([]),[selected,setSelected]=useState(''),[mode,setMode]=useState('local');
 const [pending,setPending]=useState(''),[notice,setNotice]=useState(''),[fileError,setFileError]=useState('');
 const refresh=async()=>{setFileError('');try{const response=await request<{models:LocalModel[]}>(prefix+'models/local',{},'GET');setFiles(response.models);setSelected(previous=>previous||response.models[0]?.path||'')}catch(error){setFileError(failure(error))}};
 useEffect(()=>{void refresh()},[]);
 useEffect(()=>{if(cfg?.local_model)setSelected(cfg.local_model);else if(cfg?.model)setMode('server')},[cfg?.local_model,cfg?.model]);
 const run=async(name:string,action:()=>Promise<void>)=>{setPending(name);setError('');setNotice('');try{await action()}catch(error){setError(failure(error))}finally{setPending('')}};
 if(!cfg)return <SettingsLoadState error={error} retry={reload}/>;
 const loading=localModel?.state==='loading',disabled=busy||!!pending||!!loading,ready=localModel?.state==='ready'&&cfg.local_model===selected;
 const load=()=>void run('load',async()=>{onStatus(await request<AgentStatus>(prefix+'model/load',{path:selected}));acceptCfg(await request<Settings>(prefix+'settings',{},'GET'));setNotice('모델 준비를 요청했습니다. 실행 상태가 준비됨으로 바뀌면 대화할 수 있습니다.')});
 const connect=()=>void run('models',async()=>{const response=await request<{models:{id:string}[]}>(prefix+'models',{base_url:cfg.base_url,api_key:cfg.api_key});setModels(response.models.map(model=>model.id));if(!cfg.model&&response.models.length)setCfg({...cfg,model:response.models[0].id});setNotice(response.models.length?'연결 확인 · 사용 가능한 모델 '+response.models.length+'개':'서버가 응답했지만 모델 목록은 비어 있습니다. 모델 이름을 직접 입력할 수 있습니다.')});
 const save=()=>void run('save',async()=>{acceptCfg(await request<Settings>(prefix+'settings',{base_url:cfg.base_url,api_key:cfg.api_key,model:cfg.model,local_model:''}));setNotice('모델 연결을 저장했습니다.')});
 const saveRuntime=()=>void run('runtime',async()=>{acceptCfg(await request<Settings>(prefix+'settings',{context_length:cfg.context_length??0,tool_loading:cfg.tool_loading??'native'}));if(cfg.local_model&&localModel?.running){onStatus(await request<AgentStatus>(prefix+'model/load',{path:cfg.local_model}));acceptCfg(await request<Settings>(prefix+'settings',{},'GET'))}setNotice('실행 설정을 저장했습니다. 로컬 모델을 다시 불러온 뒤 다음 작업부터 적용됩니다.')});
 return <div className="agent-settings-stack">
   <Tabs items={[{id:'local',label:'내 컴퓨터에서 실행'},{id:'server',label:'모델 서버 연결'}]} value={mode} onChange={setMode}/>
   <SettingsSection title={mode==='local'?'로컬 모델':'모델 서버'} description={mode==='local'?'모델 폴더의 GGUF 파일을 선택해 사용합니다.':'이미 실행 중인 모델 서버에 연결합니다.'}
    actions={mode==='local'?<><Status tone={ready?'good':loading?'idle':'idle'}>{ready?'준비됨':loading?'준비 중':'선택한 모델 미적재'}</Status><Button aria-label="로컬 모델 목록 새로고침" title="목록 갱신" disabled={!!pending} busy={pending==='files'} onClick={()=>void run('files',refresh)}><RefreshCw size={16}/></Button></>:undefined}>
    {busy&&<p className="ui-field-hint" role="status">작업 중에는 모델을 바꾸거나 내릴 수 없습니다.</p>}
    {mode==='local'?<>
     <ErrorMessage message={fileError}/>
     <LocalModelPicker files={files} selected={selected} onChange={setSelected} disabled={disabled}/>
     <div className="ui-settings-actions"><Button tone="primary" disabled={disabled||!selected||ready} busy={pending==='load'||!!loading} onClick={load}><Cpu size={16}/>{ready?'사용 중인 모델':loading?'모델 준비 중':'선택한 모델 불러오기'}</Button>{localModel?.state==='ready'&&<Button onClick={onChat}>대화 시작하기<ArrowRight size={15}/></Button>}{localModel?.running&&<Button disabled={disabled} busy={pending==='unload'} onClick={()=>void run('unload',async()=>{onStatus(await request<AgentStatus>(prefix+'model/unload',{}));setNotice('모델을 메모리에서 내렸습니다.')})}>모델 내리기</Button>}</div>
     <details className="ui-settings-disclosure"><summary>파일 경로 직접 입력</summary><label>GGUF 파일 경로<Input aria-label="GGUF 파일 경로" value={selected} disabled={disabled} onChange={event=>setSelected(event.target.value)}/></label></details>
    </>:<ModelServerForm cfg={cfg} setCfg={setCfg} disabled={disabled} models={models} connect={connect} save={save} connecting={pending==='models'} saving={pending==='save'}/>}
    <ErrorMessage message={error||localModel?.error||''}/>{notice&&<p className="ui-settings-notice" role="status">{notice}</p>}
   </SettingsSection>
   {cfg.model&&<ModelRuntimeControls cfg={cfg} update={setCfg} disabled={disabled} saving={pending==='runtime'} save={saveRuntime}/>}
 </div>;
}
