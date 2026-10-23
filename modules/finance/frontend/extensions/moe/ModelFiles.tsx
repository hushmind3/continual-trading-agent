import {useSystemState} from '@platform/data/Operations';
import {Panel} from '@platform/ui/Panel';
import {DataTable} from '@platform/ui/DataTable';
import {Button,ErrorMessage} from '@platform/ui/Primitives';
import {bytes} from '@platform/ui/format';
interface ModelFile {path:string;name:string;format:string;bytes:number;registered?:string}
export function ModelFiles({onPick}:{onPick:(path:string)=>void}){
 const files=useSystemState<{root:string;files:ModelFile[]}>('models');
 return <Panel title="모델 폴더 파일" description={files.data?.root} actions={<Button busy={files.loading} onClick={()=>void files.refresh()}>목록 갱신</Button>}><ErrorMessage message={files.error}/><DataTable label="실제 모델 파일" items={files.data?.files??[]} keyFor={f=>f.path} searchText={f=>f.name+' '+(f.registered??'')} columns={[{key:'name',label:'파일',render:f=>f.name},{key:'format',label:'형식',render:f=>f.format},{key:'bytes',label:'파일 크기',render:f=>bytes(f.bytes)},{key:'registered',label:'등록 슬롯',render:f=>f.registered??'미등록'},{key:'action',label:'패키지',render:f=><Button onClick={()=>onPick(f.path)}>구성 확인 · 가져오기</Button>}]}/></Panel>;
}
