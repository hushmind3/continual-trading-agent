export interface Tolerance {error:number;agreement:number}
export const defaultTolerance:Tolerance={error:1,agreement:99};
export function PrecisionTolerance({value,onChange,disabled=false}:{value:Tolerance;onChange:(value:Tolerance)=>void;disabled?:boolean}){
 return <details className="text-xs text-slate-500">
  <summary className="cursor-pointer font-medium">변환 후보 적용 기준</summary>
  <div className="mt-3 grid grid-cols-2 gap-3">
   {([{key:'error',label:'최대 상대 RMSE'},{key:'agreement',label:'최소 판단·예측방향 일치'}] as const).map(f=><label className="space-y-2" key={f.key}><span className="block">{f.label} (%)</span><input aria-label={f.label} type="number" min={0} max={100} step={.1} disabled={disabled} value={value[f.key]} onChange={e=>onChange({...value,[f.key]:Number(e.target.value)})} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-500"/></label>)}
  </div>
  <p className="mt-2 leading-5">현재 실제 입력에서 설정한 기준을 넘으면 교체를 차단합니다. 시장 전반의 수익 성능 검증과는 별개입니다.</p>
 </details>;
}
