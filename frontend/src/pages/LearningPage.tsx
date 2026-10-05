import { useWorkspace } from "../state/Workspace";
import { Legend, Progress, QueryState } from "../components/controls";
import { date, number, seconds } from "../format";
export function LearningPage() {
  const { models, status, moe } = useWorkspace();
  return (
    <>
      <QueryState {...status} />
      <QueryState {...moe} />
      <div className="mb-8 flex flex-wrap items-center gap-3 text-sm text-slate-400">
        {[
          "경험 생성",
          "결과 확정",
          "학습 대기",
          "학습 진행",
          "가중치 반영",
        ].map((step, index) => (
          <span key={step}>
            {index > 0 && <span className="mr-3 text-slate-600">→</span>}
            {step}
          </span>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        {models.map((model) => {
          const data = model.data;
          const replay = data.replay;
          return (
            <section
              key={model.role}
              className="min-w-0 border-t-2 border-white/10 pt-5"
            >
              <div className="mb-6 flex items-center justify-between">
                <h2 className="font-semibold">{model.name}</h2>
                <Legend on={model.running && !!data.learning_active}>
                  {!model.available
                    ? model.displayStatus
                    : model.running && data.learning_active
                      ? "학습 중"
                      : "대기"}
                </Legend>
              </div>
              <p className="text-4xl font-semibold tabular-nums">
                {number(data.optimizer_updates)}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                누적 가중치 업데이트
              </p>
              <dl className="my-6 space-y-3 text-sm">
                {[
                  ["결과 확정 대기", replay?.pending],
                  ["저장된 경험", replay?.total],
                  ["학습 대기", replay?.untrained],
                  ["학습 가능", replay?.eligible],
                  ["격리된 경험", replay?.quarantined],
                  ["모델 저장 대기", replay?.awaiting_checkpoint],
                ].map(([label, value]) => (
                  <div key={String(label)} className="flex justify-between">
                    <dt className="text-slate-500">{label}</dt>
                    <dd className="tabular-nums">{number(value)}</dd>
                  </div>
                ))}
              </dl>
              {replay?.storage_pressure && (
                <p className="mb-4 text-sm text-amber-200">
                  경험 저장소 용량 주의
                </p>
              )}
              {data.error && (
                <p role="alert" className="mb-4 text-xs text-rose-300">
                  {data.error}
                </p>
              )}
              <div className="border-t border-white/10 pt-4 text-xs text-slate-400">
                <p>최근 학습 {date(data.learning?.updated_at)}</p>
                <p className="mt-2">
                  오차 {number(data.learning?.loss, 6)} ·{" "}
                  {number(data.learning?.samples)}개 ·{" "}
                  {seconds(data.learning?.seconds)}
                </p>
              </div>
              <h3 className="mb-3 mt-7 text-xs font-medium">
                날짜별 경험 처리
              </h3>
              <div className="space-y-4">
                {replay?.daily?.map((day) => (
                  <div key={day.day}>
                    <div className="mb-2 flex justify-between text-xs">
                      <span>{day.day}</span>
                      <span>
                        {number(day.completed)} / {number(day.enqueued)}
                      </span>
                    </div>
                    <Progress
                      value={day.completed}
                      total={day.enqueued}
                      label={`${model.name} ${day.day} 학습 완료`}
                    />
                    <p className="mt-1 text-[11px] text-slate-500">
                      남은 경험 {number(day.remaining)} · 보류{" "}
                      {number(day.blocked)}
                    </p>
                  </div>
                )) ?? (
                  <p className="text-xs text-slate-500">처리 기록 미수신</p>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </>
  );
}
