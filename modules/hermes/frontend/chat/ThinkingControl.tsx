import {Brain} from 'lucide-react';
import {Select} from '@platform/ui/Primitives';
import type {ThinkingMode} from './useThinking';
interface Props{value:ThinkingMode;change:(value:ThinkingMode)=>void;active:boolean;local:boolean}
export function ThinkingControl({value,change,active,local}:Props){
 if(!local)return null;
 return <label className="ha-mode-select"><Brain size={14}/><Select aria-label="Thinking" title={active?'다음 요청부터 적용':'Thinking을 지원하는 로컬 모델의 다음 요청에 적용'} value={value} onChange={event=>change(event.target.value as ThinkingMode)}><option value="auto">Thinking 자동</option><option value="on">Thinking 켜기</option><option value="off">Thinking 끄기</option></Select></label>;
}
