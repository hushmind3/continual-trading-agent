import {useState} from 'react';
import {Gauge} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {request} from '../../data/api';
import type {LibraryExpert} from '../../data/library';
import {Button,Drawer,ErrorMessage} from '../../ui/Primitives';
import {bytes} from '../../ui/format';

const field='w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100';
export function ExpertConversion({item,onClose}:{item:LibraryExpert;onClose:()=>void}){
 const {state,refresh}=useOperations();const [precision,setPrecision]=useState('nf4'),[device,setDevice]=useState('auto'),[error,setError]=useState('');
 const nextSlot=(p:string)=>{let value=item.id+'_'+p,n=2;while(state?.experts.items.some(e=>e.id===value))value=item.id+'_'+p+'_'+n++;return value};
 const [slot,setSlot]=useState(()=>nextSlot('nf4'));const job=state?.library?.job,busy=Boolean(job?.busy);

 const convert=async()=>{setError('');try{await request('library/convert',{id:item.id,slot,precision,device});await refresh()}catch(e){setError(e instanceof Error?e.message:'변환 실패')}};
 return <Drawer title="정밀도 변환 후보 생성" open onClose={onClose}>
  <div className="space-y-5">
   <div className="rounded-xl bg-blue-50 p-4"><p className="flex items-center gap-2 font-semibold text-blue-900"><Gauge size={17}/>{item.name}</p><p className="mt-2 text-sm text-blue-700">{item.representation} · {bytes(item.package.bytes)}</p></div>
   <div className="grid grid-cols-3 gap-2" role="group" aria-label="변환 정밀도">{['nf4','int4','int8','bf16','fp16'].map(p=><Button key={p} disabled={busy} aria-pressed={p===precision} tone={p===precision?'primary':'neutral'} onClick={()=>{setPrecision(p);setSlot(nextSlot(p))}}>{p.toUpperCase()}</Button>)}</div>
   <p className="text-sm leading-6 text-slate-600">{precision==='nf4'?'bitsandbytes의 전용 NF4 커널로 압축 가중치를 실행합니다. 일반 Linear를 4비트로 저장하고 공유 가중치·지원하지 않는 계층은 원본 정밀도를 유지합니다. 메모리와 실제 출력 검증을 우선합니다.':precision.startsWith('int')?'일반 Linear의 고정 가중치를 저비트로 압축합니다. 임베딩·공유 가중치·지원하지 않는 계층은 원래 정밀도를 유지합니다. 압축 가중치를 구간별로 복원해 계산하므로 속도 배수로 선택하지 않으며 정상 실행과 메모리를 확인합니다.':'부동소수점 가중치를 선택한 정밀도로 변환합니다. 정수 버퍼와 원본 구조·입력 규칙은 유지합니다.'}</p>
   <label className="block space-y-2 text-sm"><span>변환 후보 슬롯</span><input className={field} value={slot} disabled={busy} onChange={e=>setSlot(e.target.value)}/></label>
   <label className="block space-y-2 text-sm"><span>변환 장치</span><select className={field} disabled={busy} value={device} onChange={e=>setDevice(e.target.value)}><option value="auto">자동 · RAM/VRAM 여유에 맞춰 CUDA 활용</option><option value="cuda:0">CUDA 지정 · VRAM 부족 시 중단</option><option value="cpu">CPU 지정</option></select></label>
   <p className="text-xs leading-5 text-slate-500">현재 API는 변환 후보 패키지를 생성합니다. 후보를 실제 검사하려면 등록 모델 실행 검사를 별도로 실행하세요. 변환 후보는 자동으로 운영 구성에 적용되지 않습니다.</p>

   <Button tone="primary" disabled={busy||!slot||Boolean(item.conversion)} busy={busy&&job?.kind==='convert'} onClick={()=>void convert()}>변환 후보 생성</Button>
   {item.conversion&&<p className="text-xs text-amber-700">다시 변환할 때는 최초 원본 Expert를 선택하세요.</p>}
   {busy&&job?.kind==='convert'&&<p className="text-sm text-blue-700" aria-live="polite">{job.detail}</p>}
   {!busy&&job?.kind==='convert'&&job.stage==='complete'&&<p className="text-sm leading-6 text-emerald-700" role="status">변환 후보가 등록되었습니다. 실제 추론 검사와 운영 구성 적용은 별도 작업입니다.</p>}
   {(error||job?.error)&&<ErrorMessage message={error||job?.error||''}/>}
  </div>
 </Drawer>;
}
