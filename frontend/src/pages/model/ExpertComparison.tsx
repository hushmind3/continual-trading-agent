import {useOperations} from '../../data/Operations';
import {Panel} from '../../ui/Panel';
import {DataTable,type Column} from '../../ui/DataTable';
import type {Expert} from '../../data/types';
import {bytes} from '../../ui/format';
import {Capability} from '../../ui/Capability';
const columns:Column<Expert>[]=[{key:'name',label:'Expert',render:e=>e.name},{key:'precision',label:'정밀도',render:e=>e.representation},
 {key:'package',label:'패키지',render:e=>bytes(e.package.bytes),sort:e=>e.package.bytes},{key:'device',label:'마지막 장치',render:e=>String(e.resources.device||'미측정')},
 {key:'ram',label:'마지막 RAM',render:e=>bytes((e.resources.peak_ram_bytes??e.resources.peak_ram_increment) as number|undefined)},
 {key:'vram',label:'마지막 VRAM',render:e=>bytes((e.resources.peak_vram_bytes??e.resources.resident_bytes) as number|undefined)}];
export function ExpertComparison(){const {state:s}=useOperations();if(!s)return null;return <Panel title="Expert 비교 · 기록된 자원" description="파일 크기와 마지막 실측값 · 새 추론 비교 실험을 실행하지 않습니다."><DataTable label="Expert 자원 비교" items={s.experts.items} columns={columns} keyFor={e=>e.id} searchText={e=>e.name+' '+e.id}/><div className="mt-5 grid gap-3 sm:grid-cols-2"><Capability name="conversion" label="자동 양자화·정밀도 검사"/><Capability name="discovery" label="금융 Expert 검색·자동 등록"/></div></Panel>}
