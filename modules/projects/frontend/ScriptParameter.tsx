import {Button,Input,Select} from '@platform/ui/Primitives';
export interface ScriptOption {name:string;kind:'text'|'number'|'switch';required:boolean;managed?:boolean;choices:string[];default:string|number|boolean|null}
const labels:Record<string,string>={Race:'플레이어 종족',EnemyRace:'상대 종족',Map:'맵 경로',AutoStart:'설치 후 게임 자동 시작',Windowed:'창 모드',Bench:'추론 성능 측정'};
const choices:Record<string,string>={Zerg:'저그',Terran:'테란',Protoss:'프로토스',Random:'무작위',Default:'기본값'};
export function ScriptParameter({option,value,onChange,disabled,onBrowse}:{option:ScriptOption;value:string|number|boolean;onChange:(value:string|boolean)=>void;disabled:boolean;onBrowse?:()=>void}){
 const label=labels[option.name]||option.name.replace(/Dir$/,' 폴더').replace(/Path$/,' 경로');
 if(option.kind==='switch')return <label className="flex items-center gap-3 text-sm"><Input type="checkbox" checked={!!value} onChange={e=>onChange(e.target.checked)} disabled={disabled}/>{label}</label>;
 return <label className="grid gap-2 text-sm"><span className="font-medium">{label}{option.required&&<span className="ml-2 text-xs text-slate-500">필수</span>}</span>{option.choices.length?<Select aria-label={label} value={String(value)} onChange={e=>onChange(e.target.value)} disabled={disabled}>{option.choices.map(item=><option key={item} value={item}>{choices[item]||item}</option>)}</Select>:<span className="flex min-w-0 gap-2"><Input aria-label={label} type={option.kind==='number'?'number':'text'} value={String(value)} required={option.required} onChange={e=>onChange(e.target.value)} disabled={disabled} placeholder={option.required?'원본 프로그램이 사용할 경로 또는 값을 지정하세요.':undefined}/>{onBrowse&&/dir$|path$/i.test(option.name)&&<Button disabled={disabled} onClick={onBrowse}>폴더 선택</Button>}</span>}</label>;
}
