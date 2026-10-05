import { Pause, Play } from "lucide-react";
import { useWorkspace } from "../state/Workspace";
import { Action, Legend, Outcome, QueryState } from "../components/controls";
import { AccountSummary } from "../components/AccountSummary";
import { DecisionView, FillList } from "../components/Execution";
import { bytes, date, number, seconds } from "../format";

export function TradingMoEPage() {
  const { moe, models, toggleModel, setSelected } = useWorkspace();
  const model = models.find((entry) => entry.role === "trading-moe")!;
  const data = model.data;
  const symbols = Object.values(data.books ?? {}).flatMap((book) =>
    Object.keys(book.positions ?? {}),
  );
  const symbol =
    data.decision?.symbol ?? (symbols.length === 1 ? symbols[0] : undefined);
  return (
    <>
      <QueryState {...moe} />
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <Legend on={model.running}>{model.displayStatus}</Legend>
        <Action
          disabled={
            !model.available ||
            model.busy ||
            ["loading", "starting", "saving", "stopping"].includes(
              data.status ?? "",
            )
          }
          primary={!model.enabled}
          onClick={() => toggleModel(model.name)}
        >
          {model.enabled ? <Pause size={16} /> : <Play size={16} />}TradingMoE{" "}
          {model.busy ? "요청 중" : model.enabled ? "저장 후 정지" : "시작"}
        </Action>
      </div>
      <Outcome forKey="trading-moe" />
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(250px,1fr)]">
        <div className="rounded-2xl bg-sky-300/5 px-6 py-4">
          <DecisionView
            decision={data.decision ? { ...data.decision, symbol } : undefined}
            live={model.running}
          />
          {data.gpu_waiting && model.running && (
            <p className="mt-3 text-sm text-amber-200">
              GPU 사용 대기 · {seconds(data.gpu_wait_seconds)}
            </p>
          )}
          <div className="mt-6 border-t border-white/10 pt-5">
            <h3 className="mb-4 text-sm font-medium">학습 상태</h3>
            <Legend on={model.running && !!data.learning_active}>
              {model.running && data.learning_active ? "학습 중" : "학습 대기"}
            </Legend>
            <dl className="mt-4 grid grid-cols-2 gap-4 text-xs">
              {[
                ["가중치 업데이트", number(data.optimizer_updates)],
                ["학습 대기 경험", number(data.replay?.untrained)],
                ["결과 확정 대기", number(data.replay?.pending)],
                ["최근 학습 오차", number(data.learning?.loss, 6)],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="mb-1 text-slate-500">{label}</dt>
                  <dd className="text-lg tabular-nums">{value}</dd>
                </div>
              ))}
            </dl>
            {data.reward_points && (
              <p className="mt-4 text-xs text-slate-400">
                누적 학습 보상 · USD {number(data.reward_points.USD, 6)} · KRW{" "}
                {number(data.reward_points.KRW, 6)}
              </p>
            )}
          </div>
        </div>
        <AccountSummary books={data.books} />
      </div>
      {data.error && (
        <p role="alert" className="my-5 text-sm text-rose-300">
          {data.error}
        </p>
      )}
      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold">최근 가상 체결</h2>
        <FillList fills={data.fills} />
      </section>
      <details className="mt-8 text-xs text-slate-500">
        <summary className="cursor-pointer">처리 과정 · 모델 정보</summary>
        <div className="mt-4 flex flex-wrap gap-3">
          {[
            ["market", "시장 분석"],
            ["state", "의견 통합"],
            ["policy", "정책 의견"],
            ["controller", "매매 판단"],
            ["action", "행동 결정"],
          ].map(([key, label]) => (
            <span
              key={key}
              className={
                data.stages?.[key] ? "text-teal-300" : "text-slate-500"
              }
            >
              {label} ·{" "}
              {data.stages?.[key] ? "최근 처리 확인" : "처리 기록 없음"}
            </span>
          ))}
        </div>
        <dl className="mt-5 space-y-2">
          <div>
            파라미터 {number(data.parameters)} · 모델 파일{" "}
            {bytes(data.checkpoint_bytes)}
          </div>
          <div>
            최근 시장 입력 {date(data.market_timestamp)} · 전체 처리{" "}
            {seconds(data.cycle_seconds)}
          </div>
        </dl>
        <button
          onClick={() => setSelected("TradingMoE")}
          className="mt-4 text-sky-300"
        >
          상태 상세
        </button>
      </details>
    </>
  );
}
