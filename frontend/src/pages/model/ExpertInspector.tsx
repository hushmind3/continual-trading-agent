import {useEffect,useState} from 'react';
import {LockKeyhole} from 'lucide-react';
import type {Expert} from '../../data/types';
import {request} from '../../data/api';
import {Drawer,Empty,ErrorMessage} from '../../ui/Primitives';
import {bytes,date,number} from '../../ui/format';
import {useOperations} from '../../data/Operations';
export function ExpertInspector({
  expert,
  close,
}: {
  expert: Expert | null;
  close: () => void;
}) {
  const {state}=useOperations();const item=expert?state?.library?.catalog.experts?.[expert.id]:undefined;
  const [output, setOutput] = useState<unknown>(null),
    [error, setError] = useState("");
  const [origin,setOrigin]=useState('');
  useEffect(() => {
    let disposed=false;
    setOutput(null);
    setError("");
    setOrigin('');
    if (expert)
      void request<{ output: unknown;origin?:string }>(
        `experts/${encodeURIComponent(expert.id)}`,
      )
        .then((x) => {if(!disposed){setOutput(x.output);setOrigin(x.origin??'운영 출력')}})
        .catch((e) => {if(!disposed)setError(e.message)});
    return ()=>{disposed=true};
  }, [expert?.id,expert?.last_as_of,item?.check.tested]);
  return (
    <Drawer
      title={expert?.name ?? "Expert"}
      open={Boolean(expert)}
      onClose={close}
    >
      {expert && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-violet-50 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-violet-700">
              <LockKeyhole size={16} />
              원본 가중치 고정
            </div>
            <p className="mt-2 text-sm leading-6 text-violet-700/70">
              {expert.role === 'action'
                ? "원래 학습한 주식과 계좌 상태로 매매 의견을 계산합니다."
                : "시장 시계열의 다음 관측을 예측해 MoE에 전달합니다."}
            </p>
          </div>
          {expert.error && <ErrorMessage message={expert.error} />}
          {item&&<section className="space-y-3 text-sm">
            <h3 className="font-semibold">이 Expert의 검사 기준</h3>
            <ul className="space-y-2 text-xs leading-5 text-slate-500">
              <li>입력 연결: {item.input.requires?.join(' · ')??item.input.reason}</li>
              <li>실행 검사: 실제 관측으로 추론 성공 · 출력 크기·유한값 확인 · frozen 가중치 유지 · 시간·메모리 측정</li>
              <li>검사 결과: {item.check.detail}</li>
              <li>종목 범위: {item.input.universe?.length?`원본 학습 ${item.input.universe.length}종목. 모델의 원래 종목 순서와 관측 규칙을 사용합니다.`:'시계열이 확보된 관찰 종목에 공통 적용합니다. 시스템의 종목 수는 고정하지 않습니다.'}</li>
              {item.conversion?.validation&&<li>변환 적용 기준: 상대 RMSE ≤ {number(item.conversion.validation.max_relative_rmse*100,2)}% · 판단·예측방향 일치 ≥ {number(item.conversion.validation.min_action_agreement*100,2)}%. 현재 오차 {number(item.conversion.validation.relative_rmse*100,4)}%{item.conversion.validation.action_agreement!=null?` · 판단 일치 ${number(item.conversion.validation.action_agreement*100,2)}%`:''}{item.conversion.validation.direction_agreement!=null?` · 예측방향 일치 ${number(item.conversion.validation.direction_agreement*100,2)}%`:''}.</li>}
              {item.check.metrics?.device_reason&&<li>장치 배분: {item.check.metrics.device_reason}</li>}
            </ul>
          </section>}
          <dl className="grid grid-cols-2 gap-x-4 gap-y-5 text-sm">
            <Detail label="파라미터" value={number(expert.parameters, 0)} />
            <Detail
              label="실행 장치"
              value={expert.device ?? "아직 실행 안 됨"}
            />
            {expert.inference_seconds != null && (
              <Detail
                label="최근 분석 시간"
                value={`${number(expert.inference_seconds, 3)}s`}
              />
            )}
            <Detail label="마지막 입력" value={date(expert.last_as_of)} />
            {expert.peak_vram_bytes != null && (
              <Detail
                label="측정된 GPU peak"
                value={bytes(expert.peak_vram_bytes)}
              />
            )}
          </dl>
          {(expert.symbols ?? expert.universe ?? item?.input.universe)?.length ? (
            <div>
              <h3 className="mb-3 text-sm font-semibold">원래 학습한 종목</h3>
              <div className="flex flex-wrap gap-1.5">
                {(expert.symbols ?? expert.universe ?? item?.input.universe)!.map((s) => (
                  <span
                    key={s}
                    className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-500"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
          {error && <ErrorMessage message={error} />}
          <details className="border-t border-slate-100 pt-4">
            <summary className="cursor-pointer text-sm font-medium text-slate-500">
              {origin||'출력'} · 진단
            </summary>
            {expert.weight_files?.length ? <p className="mt-3 break-all text-xs text-slate-500">실제로 읽은 모델 파일: {expert.weight_files.join(', ')}</p> : null}
            {output ? (
              <pre className="mt-3 max-h-96 overflow-auto rounded-xl bg-slate-950 p-4 text-[11px] leading-5 text-slate-300">
                {JSON.stringify(output, null, 2)}
              </pre>
            ) : (
              <Empty title="저장된 실제 출력이 없습니다." />
            )}
            <p className="mt-2 font-mono text-xs text-slate-400">{expert.id}</p>
          </details>
        </div>
      )}
    </Drawer>
  );
}
function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="mb-1 text-xs text-slate-400">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}
