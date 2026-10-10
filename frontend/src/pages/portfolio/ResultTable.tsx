import {useEndpoint} from '../../data/useEndpoint';
import type {ResultTable as Result} from '../../data/types';
import {DataTable} from '../../ui/DataTable';
import {Empty,ErrorMessage,Button} from '../../ui/Primitives';
import {number} from '../../ui/format';
export function ResultTable({kind}:{kind:'weights'|'trades'}){const result=useEndpoint<Result>('result/'+kind);
 return <div className="space-y-4"><div className="flex justify-between gap-3"><p className="text-xs text-slate-400">원본 BacktestResult · 전체 {result.data?.total??0}행 / 최근 최대 1,000행</p><Button onClick={()=>void result.refresh()} busy={result.loading}>내역 새로고침</Button></div><ErrorMessage message={result.error}/>{result.data?.rows.length?<DataTable<Record<string,unknown>&{_key:string}> label={kind==='weights'?'포트폴리오 가중치':'백테스트 거래'} items={result.data.rows.map((r,index)=>({...r,_key:String(index)}))} keyFor={r=>r._key} columns={result.data.columns.map(key=>({key,label:key,render:r=>typeof r[key]==='number'?number(r[key] as number,5):String(r[key]??'미기록')}))}/>:<Empty title="저장된 내역이 없습니다." detail="공식 백테스트 완료 후 생성됩니다."/>}</div>;
}
