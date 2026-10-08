import {useState} from 'react';
import {FlaskConical} from 'lucide-react';
import {useOperations} from '../../data/Operations';
import {request} from '../../data/api';
import {Button,ErrorMessage} from '../../ui/Primitives';
import {bytes,number,percent} from '../../ui/format';

interface Measurement {id:string;cold_seconds:number;warm_median_seconds:number;warm_min_seconds:number;warm_max_seconds:number;metrics:{device:string;peak_ram_bytes:number;peak_vram_bytes:number}}
interface Result {baseline:Measurement;variant:Measurement;input_as_of:string;input_sha256:string;symbols:string[];mean_absolute_error:number;max_absolute_error:number;relative_rmse:number;action_agreement:number|null;speed_ratio:number;file_bytes:Record<string,number>;scope:string}
export function ExpertComparison(){
 const {state,refresh}=useOperations();const [a,setA]=useState(''),[b,setB]=useState(''),[device,setDevice]=useState('cpu'),[error,setError]=useState('');
 const lib=state?.library;const choices=Object.values(lib?.catalog.experts??{}).filter(e=>e.input.supported);
 const result=(lib?.job.kind==='compare'&&lib.job.stage==='complete'?lib.job.result:lib?.catalog.comparison) as Result|undefined;
 const busy=Boolean(lib?.job.busy);
 const compare=async()=>{setError('');try{await request('library/compare',{baseline:a,variant:b,device,repeats:3});await refresh()}catch(e){setError(e instanceof Error?e.message:'비교 실패')}};
 const select='rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-violet-500';
 return <section className="space-y-4 rounded-2xl bg-violet-50/70 p-5">
  <header><h3 className="flex items-center gap-2 text-sm font-bold text-violet-900"><FlaskConical size={16}/>출력 · 속도 · 메모리 비교</h3><p className="mt-1 text-xs leading-5 text-slate-500">같은 실제 입력을 고정하고, 각 모델을 별도 프로세스에서 3회 측정합니다. 계좌 체결과 학습 상태는 바꾸지 않습니다.</p></header>
  <div className="flex flex-wrap gap-2">
   <select aria-label="기준 Expert" className={select} value={a} onChange={e=>setA(e.target.value)}><option value="">기준 Expert</option>{choices.map(e=><option key={e.id} value={e.id}>{e.name} · {e.id}</option>)}</select>
   <select aria-label="비교 Expert" className={select} value={b} onChange={e=>setB(e.target.value)}><option value="">비교 Expert</option>{choices.map(e=><option key={e.id} value={e.id}>{e.name} · {e.id}</option>)}</select>
   <select aria-label="실험 장치" className={select} value={device} onChange={e=>setDevice(e.target.value)}><option value="cpu">CPU</option><option value="auto">가용 장치 자동</option><option value="cuda:0">GPU 가능 여부 확인</option></select>
   <Button tone="primary" busy={busy&&lib?.job.kind==='compare'} disabled={busy||!a||!b} onClick={()=>void compare()}>동일 입력 비교</Button>
  </div>
  {error&&<ErrorMessage message={error}/>}
  {lib?.job.kind==='compare'&&lib.job.error&&<ErrorMessage message={lib.job.error}/>}
  {busy&&lib?.job.kind==='compare'&&<p className="text-sm text-violet-700" aria-live="polite">{lib.job.detail}</p>}
  {result&&<div className="space-y-4">
   <p className="text-xs text-slate-500">입력 {result.input_as_of} · {result.symbols.length}종목 · 동일 입력 SHA256 {result.input_sha256.slice(0,12)}</p>
   <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs text-slate-500"><tr><th className="py-2">측정</th><th>기준</th><th>비교 대상</th></tr></thead><tbody>
    {[
     ['실행 장치',result.baseline.metrics.device,result.variant.metrics.device],
     ['파일 크기',bytes(result.file_bytes[result.baseline.id]),bytes(result.file_bytes[result.variant.id])],
     ['첫 적재 · 추론',number(result.baseline.cold_seconds,3)+'s',number(result.variant.cold_seconds,3)+'s'],
     ['반복 추론 중앙값',number(result.baseline.warm_median_seconds,4)+'s',number(result.variant.warm_median_seconds,4)+'s'],
     ['프로세스 peak RAM',bytes(result.baseline.metrics.peak_ram_bytes),bytes(result.variant.metrics.peak_ram_bytes)],
     ['peak VRAM',bytes(result.baseline.metrics.peak_vram_bytes),bytes(result.variant.metrics.peak_vram_bytes)]
    ].map(row=><tr key={row[0]} className="border-t border-violet-100"><td className="py-2 text-slate-500">{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>)}
   </tbody></table></div>
   <p className="text-sm text-violet-900">출력 평균 절대오차 {number(result.mean_absolute_error,6)} · 최대오차 {number(result.max_absolute_error,6)} · 상대 RMSE {percent(result.relative_rmse)}{result.action_agreement!=null?` · 판단 일치 ${percent(result.action_agreement)}`:''} · 속도 {number(result.speed_ratio,2)}배</p>
   <p className="text-xs leading-5 text-slate-500">{result.scope} OS 파일 캐시와 운영 부하는 측정값에 영향을 줄 수 있습니다.</p>
  </div>}
 </section>;
}
