import {Brain} from 'lucide-react';
import {Select,ErrorMessage} from '@platform/ui/Primitives';

export interface CodexModel {id:string;name:string;aliases?:string[];default_reasoning_effort?:string;reasoning_efforts:{value:string;description:string;available:boolean}[]}
export interface ReasoningSelection {model?:CodexModel;value:string;change:(value:string)=>void;error?:string}
const labels:Record<string,string>={none:'끄기',minimal:'최소',low:'낮음 · 가벼운 추론',medium:'보통',high:'높음',xhigh:'매우 높음',max:'최대',ultra:'최상위'};
const reasoningDescriptions:Record<string,string>={
 'Greater reasoning depth for complex problems':'복잡한 문제를 해결할 때 더 깊이 추론합니다.',
};
export function ReasoningSelect({model,value,change,error,disabled,compact=false}:ReasoningSelection&{disabled?:boolean;compact?:boolean}){
 const options=model?.reasoning_efforts??[],defaultLabel=model?.default_reasoning_effort;
 const description=options.find(row=>row.value===value)?.description;
 return <><label className={compact?'ha-mode-select ha-reasoning-select':undefined}>{compact?<><Brain size={14}/><span>추론</span></>:<span>추론 수준</span>}<Select aria-label="추론 수준" disabled={disabled||!model} value={value} title={description?(reasoningDescriptions[description]||description):'다음 요청부터 적용'} onChange={event=>change(event.target.value)}><option value="auto">모델 기본값{defaultLabel?' · '+(labels[defaultLabel]||defaultLabel):''}</option>{options.map(row=><option key={row.value} value={row.value} disabled={!row.available}>{labels[row.value]||row.value}{!row.available?' · Codex 전용, 현재 미지원':''}</option>)}</Select></label>{!compact&&options.some(row=>!row.available)&&<p className="ui-field-hint">서버가 제공하는 선택지를 모두 표시합니다. Codex 자동 위임 등 현재 Choki 전송이 지원하지 않는 모드는 선택할 수 없으며 낮은 수준으로 바꿔 실행하지 않습니다.</p>}<ErrorMessage message={error||''}/></>;
}
