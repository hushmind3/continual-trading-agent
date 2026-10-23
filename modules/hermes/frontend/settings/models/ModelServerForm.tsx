import {Button,Input} from '@platform/ui/Primitives';
import type {Settings} from '../../types';
interface Props {cfg:Settings;setCfg:(value:Settings)=>void;disabled:boolean;models:string[];connect:()=>void;save:()=>void;connecting:boolean;saving:boolean}
export function ModelServerForm({cfg,setCfg,disabled,models,connect,save,connecting,saving}:Props) {
  return <form className="ui-settings-fields" onSubmit={event=>{event.preventDefault();save()}}>
    <label>모델 서버 주소<Input required type="url" value={cfg.base_url} disabled={disabled} onChange={event=>setCfg({...cfg,base_url:event.target.value})}/></label>
    <label>접속 키<Input type="password" autoComplete="off" value={cfg.api_key} disabled={disabled} onChange={event=>setCfg({...cfg,api_key:event.target.value})} placeholder={cfg.has_api_key?'저장됨 · 비우면 기존 키 유지':'필요한 서버만 입력'}/></label>
    <div className="agent-server-model-row"><label>사용할 모델<Input required list="hermes-server-models" value={cfg.model} disabled={disabled} onChange={event=>setCfg({...cfg,model:event.target.value})}/><datalist id="hermes-server-models">{models.map(id=><option key={id} value={id}/>)}</datalist></label><Button type="button" disabled={disabled} busy={connecting} onClick={connect}>연결 확인</Button></div>
    <div><Button type="submit" tone="primary" disabled={disabled} busy={saving}>이 모델 사용</Button></div>
  </form>;
}
