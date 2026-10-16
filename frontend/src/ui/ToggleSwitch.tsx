import {Button} from './Primitives';
interface Props {label:string;checked:boolean;onChange:(value:boolean)=>void;disabled?:boolean;title?:string}
export function ToggleSwitch({label,checked,onChange,disabled,title}:Props){
 return <Button type="button" role="switch" aria-label={label} aria-checked={checked} disabled={disabled} title={title} onClick={()=>onChange(!checked)} className="ui-toggle-switch">
  <span className="ui-switch-track" aria-hidden="true"><span/></span><span>{label}</span>
 </Button>;
}
