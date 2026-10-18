import {Button,Input,Select} from '@platform/ui/Primitives';
import {SettingsSection} from '@platform/ui/SettingsSection';
import type {Settings} from '../../types';
interface Props {cfg:Settings;update:(value:Settings)=>void;disabled:boolean;saving:boolean;save:()=>void}
export function ModelRuntimeControls({cfg,update,disabled,saving,save}:Props){
 return <SettingsSection title="실행 설정" description={`현재 모델: ${cfg.model}`}>
  <form className="ui-settings-fields" onSubmit={event=>{event.preventDefault();save()}}>
   {cfg.local_model&&<><label>문맥 한도<Input aria-label="문맥 한도" type="number" min={0} max={2097152} step={1} value={cfg.context_length??0} disabled={disabled} onChange={event=>update({...cfg,context_length:Number(event.target.value)})}/><span className="ui-field-hint">0은 모델 기본값입니다. 한도가 크면 GPU 메모리가 부족해 느려질 수 있습니다. 변경 적용 시 모델을 다시 불러옵니다.</span></label>
   <label>Thinking<Select aria-label="Thinking" value={cfg.thinking_mode??'auto'} disabled={disabled} onChange={event=>update({...cfg,thinking_mode:event.target.value as Settings['thinking_mode']})}><option value="auto">모델 기본값</option><option value="on">켜기</option><option value="off">끄기</option></Select><span className="ui-field-hint">Thinking 전환을 지원하는 로컬 모델에 적용합니다.</span></label></>}
   <label>도구 설명 불러오기<Select aria-label="도구 설명 불러오기" value={cfg.tool_loading??'native'} disabled={disabled} onChange={event=>update({...cfg,tool_loading:event.target.value as Settings['tool_loading']})}><option value="lazy">필요할 때 불러오기</option><option value="native">Hermes 원본 기본값</option><option value="eager">처음부터 모두 불러오기</option></Select><span className="ui-field-hint">도구 기능은 유지하고, 모델에 설명을 전달하는 시점만 바꿉니다. 다음 작업부터 적용됩니다.</span></label>
   <div><Button type="submit" tone="primary" disabled={disabled} busy={saving}>실행 설정 저장·적용</Button></div>
  </form>
 </SettingsSection>;
}
