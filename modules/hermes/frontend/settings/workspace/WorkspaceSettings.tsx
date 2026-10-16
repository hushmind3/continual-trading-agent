import {useState} from 'react';
import {Button,Input,ErrorMessage} from '@platform/ui/Primitives';
import {SettingsSection,SettingsLoadState} from '@platform/ui/SettingsSection';
import {request} from '@platform/data/api';
import {prefix,failure,type Settings} from '../../types';
import {useAgentSettings} from '../useAgentSettings';
const tools={file:'파일·코드 수정',terminal:'명령 실행',todo:'작업 계획',skills:'스킬 활용',browser:'웹 브라우저',computer_use:'컴퓨터 조작',memory:'기억'};
export function WorkspaceSettings({busy}:{busy:boolean}) {
  const {cfg,setCfg,acceptCfg,error,setError,reload}=useAgentSettings();
  const [pending,setPending]=useState(false),[notice,setNotice]=useState('');
  if(!cfg)return <SettingsLoadState error={error} retry={reload}/>;
  const save=async()=>{setPending(true);setError('');setNotice('');try{acceptCfg(await request<Settings>(prefix+'settings',{workspace:cfg.workspace,toolsets:cfg.toolsets,max_iterations:cfg.max_iterations}));setNotice('작업 환경을 저장했습니다. 다음 작업부터 적용됩니다.')}catch(error){setError(failure(error))}finally{setPending(false)}};
  return <div className="agent-settings-stack"><SettingsSection title="작업 폴더와 도구" description="에이전트가 작업할 위치와 사용할 기능을 정합니다.">
    {busy&&<p className="ui-field-hint" role="status">작업 중에는 설정을 저장할 수 없습니다. 현재 작업이 끝난 뒤 저장하세요.</p>}
    <form className="ui-settings-fields" onSubmit={event=>{event.preventDefault();void save()}}>
      <label>작업 폴더<Input required value={cfg.workspace} disabled={pending} onChange={event=>setCfg({...cfg,workspace:event.target.value})}/></label>
      <fieldset disabled={pending}><legend>사용할 기능</legend><div className="agent-tool-grid">{Object.entries(tools).map(([id,label])=><label key={id}><Input type="checkbox" checked={cfg.toolsets.includes(id)} onChange={event=>setCfg({...cfg,toolsets:event.target.checked?[...cfg.toolsets,id]:cfg.toolsets.filter(tool=>tool!==id)})}/><span>{label}</span></label>)}</div></fieldset>
      <label>최대 작업 반복 횟수<Input type="number" required min={1} max={10000} value={cfg.max_iterations} disabled={pending} onChange={event=>setCfg({...cfg,max_iterations:Number(event.target.value)})}/></label>
      <ErrorMessage message={error}/>{notice&&<p className="ui-settings-notice" role="status">{notice}</p>}
      <div><Button type="submit" tone="primary" disabled={pending||busy} busy={pending}>작업 환경 저장</Button></div>
    </form>
  </SettingsSection><SettingsSection title="실행 환경"><dl className="ui-setting-facts"><div><dt>파이썬</dt><dd>{cfg.python}</dd></div><div><dt>컴퓨터 조작 실행기</dt><dd>{cfg.computer_driver_installed?'설치됨':'설치 필요'}</dd></div><div><dt>브라우저 실행기</dt><dd>{cfg.browser_runtime_installed?'설치됨':'설치 확인 필요'}</dd></div></dl></SettingsSection></div>;
}
