import {useState} from 'react';
import {Gauge} from 'lucide-react';
import type {Expert} from '../../data/types';
import {useOperations} from '../../data/Operations';
import {Button,Drawer,ErrorMessage,inputClass} from '../../ui/Primitives';
import {bytes} from '../../ui/format';
import {PrecisionTolerance,defaultTolerance} from './PrecisionTolerance';

type Mode='convert'|'optimize';
export function ExpertConversion({item,onClose,initialMode='convert'}:{item:Expert;onClose:()=>void;initialMode?:Mode}) {
 const {state,execute,pending}=useOperations();
 const [mode,setMode]=useState<Mode>(initialMode);
 const [precision,setPrecision]=useState('nf4'),[device,setDevice]=useState('auto'),[error,setError]=useState('');
 const slotFor=(value:string)=>{let slot=item.id+'_'+value,index=2;while(state?.experts.items.some(e=>e.id===slot)){slot=item.id+'_'+value+'_'+index++;}return slot;};
 const [slot,setSlot]=useState(()=>slotFor('nf4'));
 const [tolerance,setTolerance]=useState(defaultTolerance),[referenceCheck,setReferenceCheck]=useState(false);
 const job=state?.library?.job,busy=Boolean(job?.busy||state?.job.running);
 const changePrecision=(value:string)=>{setPrecision(value);setSlot(slotFor(value));};
 const run=async()=>{
  setError('');
  if(mode==='convert'&&!/^[a-z][a-z0-9_]{0,79}$/.test(slot)){setError('새 슬롯 이름은 영문 소문자로 시작하고 소문자·숫자·밑줄만 사용할 수 있습니다.');return;}
  if(mode==='convert'&&state?.experts.items.some(e=>e.id===slot)){setError('이미 등록된 슬롯입니다. 다른 이름을 사용하세요.');return;}
  try{
   const payload=mode==='convert'
    ?{id:item.id,slot,precision,device}
    :{id:item.id,device,goal:'memory',precisions:['nf4','int4','int8'],validation_mode:referenceCheck?'reference':'functional',max_relative_rmse:tolerance.error/100,min_action_agreement:tolerance.agreement/100};
   await execute('library/'+mode,payload);
   onClose();
  }catch(e){setError(e instanceof Error?e.message:'Expert 작업 요청 실패');}
 };
 return <Drawer title={item.name+' · 정밀도 관리'} open onClose={onClose}>
  <div className="space-y-5">
   <div className="rounded-xl bg-blue-50 p-4"><p className="flex items-center gap-2 font-semibold text-blue-900"><Gauge size={17}/>{item.name}</p><p className="mt-2 text-sm text-blue-700">{item.representation||'원본'} · {bytes(item.package.bytes)}</p></div>
   <div className="flex flex-wrap gap-2"><Button tone={mode==='convert'?'primary':'neutral'} disabled={busy} onClick={()=>setMode('convert')}>정밀도 변환</Button><Button tone={mode==='optimize'?'primary':'neutral'} disabled={busy} onClick={()=>setMode('optimize')}>자동 양자화·원본 비교</Button></div>
   {mode==='convert'?<>
    <div className="grid grid-cols-3 gap-2" role="group" aria-label="변환 정밀도">{['nf4','int4','int8','bf16','fp16'].map(p=><Button key={p} disabled={busy} aria-pressed={p===precision} tone={p===precision?'primary':'neutral'} onClick={()=>changePrecision(p)}>{p.toUpperCase()}</Button>)}</div>
    <p className="text-sm leading-6 text-slate-600">{precision==='nf4'?'NF4 압축 가중치 버전을 별도 저장합니다.':precision.startsWith('int')?'선택한 비트 수의 Linear 가중치 압축 후보를 만듭니다.':'선택한 부동소수점 정밀도의 독립 후보를 만듭니다.'}</p>
    <label className="block space-y-2 text-sm"><span>새 변환 후보 슬롯</span><input className={inputClass} value={slot} disabled={busy} onChange={e=>setSlot(e.target.value)}/></label>
    <p className="text-xs leading-5 text-slate-500">변환 요청은 별도 후보를 생성합니다. 실제 입력 비교·품질 합격은 자동 양자화 또는 Expert 비교를 따로 실행해 확인합니다. 원본과 현재 사용 구성은 유지됩니다.</p>
   </>:<>
    <p className="text-sm leading-6 text-slate-600">원본과 NF4 / INT4 / INT8 후보를 같은 실제 입력으로 측정하고, 기존 품질 검사 기준과 자원 여유를 적용해 최적 후보를 기록합니다. 자동으로 사용 구성을 교체하지 않습니다.</p>
    <label className="flex items-center gap-2 text-xs text-slate-500"><input type="checkbox" checked={referenceCheck} disabled={busy} onChange={e=>setReferenceCheck(e.target.checked)}/>원본 근사 오차 기준을 합격 조건으로 적용</label>
    {referenceCheck&&<PrecisionTolerance value={tolerance} onChange={setTolerance} disabled={busy}/>}
   </>}
   <label className="block space-y-2 text-sm"><span>변환·추론 장치</span><select className={inputClass} disabled={busy} value={device} onChange={e=>setDevice(e.target.value)}><option value="auto">자동 · RAM/VRAM 여유에 따라 선택</option><option value="cuda:0">CUDA 지정 · VRAM 부족 시 중단</option><option value="cpu">CPU 지정</option></select></label>
   <ErrorMessage message={error||''}/>
   <Button tone="primary" disabled={busy||Boolean(item.conversion)||item.executor==='llama_cpp'||(mode==='convert'&&!slot)} busy={pending.has('library/'+mode)} onClick={()=>void run()}>{mode==='convert'?'변환 후보 생성':'자동 양자화 · 실제 입력 비교 시작'}</Button>
   {job?.busy&&<p className="text-xs text-blue-700">기존 모델 작업이 진행 중입니다. 종료 후 실행할 수 있습니다.</p>}
  </div>
 </Drawer>;
}
