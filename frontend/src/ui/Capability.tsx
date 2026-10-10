import {useOperations} from '../data/Operations';
import {Status,Button} from './Primitives';
const labels={supported:'지원',not_connected:'미연결',removed:'현재 실행 경로에서 제거',requires_configuration:'연결 설정 필요'};
export function Capability({name,label}:{name:string;label:string}) {
  const {state}=useOperations();const item=state?.capabilities[name];
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold">{label}</h3><Status tone={item?.status==='supported'?'good':'warn'}>{item?labels[item.status]:'조회 중'}</Status></div><p className="mt-2 text-xs leading-6 text-slate-500">{item?.reason||'기능 구현 여부를 조회하고 있습니다.'}</p>{item?.status!=='supported'&&<Button className="mt-3 text-xs" disabled>{label} · 사용 불가</Button>}</div>;
}
