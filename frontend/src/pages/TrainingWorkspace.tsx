import { useState } from "react";
import {
  ArrowRight,
  Check,
  Clock3,
  Database,
  History,
  RotateCcw,
  Workflow,
} from "lucide-react";
import { useOperations } from "../data/Operations";
import { request } from "../data/api";
import { ControlButton } from "../ui/ControlButton";
import {
  Button,
  Empty,
  ErrorMessage,
  Meter,
  Skeleton,
  Status,
} from "../ui/Primitives";
import { bytes, date, number, workerState } from "../ui/format";

export function TrainingWorkspace() {
  const { state, refresh } = useOperations();
  const [error, setError] = useState(""),
    [busy, setBusy] = useState("");
  const [evaluation, setEvaluation] = useState<{
    return_rate: number;
    max_drawdown: number;
    observations: number;
  } | null>(null);
  if (!state) return <Skeleton />;
  const learner = state.learner,
    status = workerState(state.workers.learner),
    batch = state.settings.learning.batch_size;
  const restore = async (file: string) => {
    setError("");
    setBusy(file);
    try {
      await request("policies/rollback", { file });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "복원 실패");
    } finally {
      setBusy("");
    }
  };
  const evaluate = async () => {
    setError("");
    setBusy("evaluation");
    try {
      setEvaluation(await request("evaluation", { currency: "USD" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "평가 실패");
    } finally {
      setBusy("");
    }
  };
  return (
    <div className="space-y-6">
      <section className="rounded-2xl bg-[#edf0fc] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-medium text-violet-600">
              <Workflow size={15} />
              TorchRL PPO
            </div>
            <h2 className="mt-2 text-2xl font-bold">
              실제 손익으로 가중치 업데이트
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
              Expert는 고정합니다. 기존 MoE 결합부와 비중 Allocator를 별도 CPU
              프로세스에서 학습합니다.
            </p>
          </div>
          <div className="space-y-3 text-right">
            <Status tone={status.tone}>{status.label}</Status>
            <ControlButton name="learning" label="학습" />
          </div>
        </div>
        <div className="mt-6 grid gap-5 sm:grid-cols-3">
          <Count
            label="기존 MoE 학습"
            value={number(state.agent.source_updates, 0) + "회"}
          />
          <Count
            label="TorchRL 가중치 업데이트"
            value={number(learner.optimizer_steps ?? 0, 0) + "회"}
          />
          <Count
            label="현재 정책"
            value={
              state.current_policy
                ? `v${state.current_policy.version}`
                : "첫 실행 대기"
            }
          />
        </div>
      </section>
      <section className="rounded-2xl bg-white px-5 py-6 shadow-sm ring-1 ring-slate-200/50">
        <div className="grid gap-5 sm:grid-cols-4">
          {[
            {
              title: "행동 · 체결",
              value: state.replay.pending,
              note: "다음 시장 결과 대기",
              icon: Clock3,
            },
            {
              title: "결과 확정",
              value: state.replay.total,
              note: "비용 반영 순자산 변화",
              icon: Database,
            },
            {
              title: "학습 대기",
              value: state.replay.ready,
              note: `동일 구성 ${batch}개 단위`,
              icon: Workflow,
            },
            {
              title: "학습 완료",
              value: state.replay.completed,
              note: "정책 · 처리 여부 저장",
              icon: Check,
            },
          ].map((phase, i) => (
            <div key={phase.title} className="relative">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <phase.icon size={15} />
                {phase.title}
              </div>
              <div className="mt-2 text-3xl font-bold tabular-nums">
                {number(phase.value, 0)}
              </div>
              <p className="mt-2 text-xs text-slate-400">{phase.note}</p>
              {i < 3 && (
                <ArrowRight
                  size={15}
                  className="absolute right-2 top-7 hidden text-slate-200 sm:block"
                />
              )}
            </div>
          ))}
        </div>
        <div className="mt-6 border-t border-slate-100 pt-4">
          <Meter
            value={(state.replay.ready / batch) * 100}
            label="다음 학습 배치"
            detail={`${Math.min(state.replay.ready, batch)} / ${batch}`}
            color="bg-violet-500"
          />
        </div>
      </section>
      {error && <ErrorMessage message={error} />}
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-white px-5 py-4">
        <div>
          <h3 className="text-sm font-bold">기록된 비중 평가</h3>
          <p className="mt-1 text-xs text-slate-400">
            실제 가격·비중 기록에 다음 관측 체결과 설정 비용을 적용합니다.
          </p>
          {evaluation && (
            <p className="mt-3 text-sm text-slate-600">
              {evaluation.observations}개 관측 · 수익률{" "}
              {number(evaluation.return_rate * 100)}% · 최대 손실폭{" "}
              {number(Math.abs(evaluation.max_drawdown) * 100)}%
            </p>
          )}
        </div>
        <Button busy={busy === "evaluation"} onClick={() => void evaluate()}>
          달러 기록 평가
        </Button>
      </section>
      <div className="grid gap-6 lg:grid-cols-[.8fr_1.2fr]">
        <section>
          <h3 className="mb-4 text-sm font-bold">최근 학습 측정</h3>
          <dl className="space-y-4 text-sm">
            {[
              {
                label: "최근 손실",
                value:
                  learner.loss != null
                    ? number(learner.loss, 6)
                    : "측정 기록 없음",
              },
              {
                label: "학습 속도",
                value:
                  learner.samples_per_second != null
                    ? `${number(learner.samples_per_second)} 경험/s`
                    : "측정 대기",
              },
              {
                label: "최근 배치 시간",
                value:
                  learner.seconds != null
                    ? `${number(learner.seconds, 3)}s`
                    : "측정 대기",
              },
              { label: "경험 저장 크기", value: bytes(state.replay.bytes) },
              {
                label: "정책 지연으로 학습 제외",
                value: `${number(state.replay.outdated, 0)}개`,
              },
            ].map((v) => (
              <div key={v.label} className="flex justify-between gap-4">
                <dt className="text-slate-400">{v.label}</dt>
                <dd className="font-medium tabular-nums">{v.value}</dd>
              </div>
            ))}
          </dl>
          <details className="mt-6 border-t border-slate-200/70 pt-4">
            <summary className="cursor-pointer text-xs font-semibold text-slate-500">
              학습 설정
            </summary>
            <dl className="mt-4 space-y-2 text-xs text-slate-400">
              <div>Learning rate {state.settings.learning.learning_rate}</div>
              <div>
                배치 {batch} · Epoch {state.settings.learning.epochs}
              </div>
              <div>PPO clip {state.settings.learning.clip_epsilon}</div>
              <div>CPU {state.settings.learning.cpu_threads} threads</div>
            </dl>
          </details>
        </section>
        <section className="overflow-hidden rounded-2xl bg-white">
          <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-sm font-bold">
            <History size={16} className="text-violet-500" />
            저장된 정책 버전
          </div>
          {state.revisions.length ? (
            <div>
              {state.revisions.map((revision) => (
                <div
                  className="flex items-center justify-between gap-3 border-b border-slate-50 px-5 py-4 last:border-0"
                  key={revision.file}
                >
                  <div>
                    <div className="text-sm font-semibold">
                      v{revision.version}{" "}
                      {revision.file === state.current_policy?.file && (
                        <span className="ml-2 text-xs font-normal text-blue-500">
                          적용 버전
                        </span>
                      )}
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                      {date(revision.time)} · {bytes(revision.bytes)}
                    </div>
                  </div>
                  <Button
                    className="px-3 py-2 text-xs"
                    busy={busy === revision.file}
                    disabled={
                      state.controls.engine ||
                      Boolean(state.workers.agent.alive) ||
                      Boolean(state.workers.learner.alive)
                    }
                    onClick={() => void restore(revision.file)}
                  >
                    <RotateCcw size={13} />
                    복원
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="첫 MoE 실행 후 초기 버전이 저장됩니다." />
          )}
          <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-400">
            복원은 MoE 정지 후 가능합니다. Expert 원본을 복제하지 않습니다.
          </p>
        </section>
      </div>
    </div>
  );
}
function Count({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-2 text-xl font-bold tabular-nums">{value}</div>
    </div>
  );
}
