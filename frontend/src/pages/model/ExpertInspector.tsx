import {useEffect,useState} from 'react';
import {LockKeyhole} from 'lucide-react';
import type {Expert} from '../../data/types';
import {request} from '../../data/api';
import {Drawer,Empty,ErrorMessage} from '../../ui/Primitives';
import {bytes,date,number} from '../../ui/format';
export function ExpertInspector({
  expert,
  close,
}: {
  expert: Expert | null;
  close: () => void;
}) {
  const [output, setOutput] = useState<unknown>(null),
    [error, setError] = useState("");
  useEffect(() => {
    setOutput(null);
    setError("");
    if (expert)
      void request<{ output: unknown }>(
        `experts/${encodeURIComponent(expert.id)}`,
      )
        .then((x) => setOutput(x.output))
        .catch((e) => setError(e.message));
  }, [expert?.id]);
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
          {(expert.symbols ?? expert.universe)?.length ? (
            <div>
              <h3 className="mb-3 text-sm font-semibold">원래 학습한 종목</h3>
              <div className="flex flex-wrap gap-1.5">
                {(expert.symbols ?? expert.universe)!.map((s) => (
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
              출력 · 진단
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
