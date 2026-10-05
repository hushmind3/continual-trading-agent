import { ArrowUpRight, Pause, Play } from "lucide-react";
import { Action, Legend, Outcome } from "./controls";
import { AccountSummary } from "./AccountSummary";
import { DecisionView, FillList } from "./Execution";
import type { RuntimeModel } from "../state/Workspace";
import { bytes, number, date, actionLabel, percent } from "../format";
type Props = {
  model: RuntimeModel;
  selected: boolean;
  learning: boolean;
  onSelect: () => void;
  onToggle: () => void;
};
export function ModelCard({
  model,
  selected,
  learning,
  onSelect,
  onToggle,
}: Props) {
  return (
    <section
      className={`relative flex min-h-[242px] flex-col rounded-2xl border p-5 transition duration-200 ${selected ? "border-sky-300 bg-[#24374b]" : "border-white/8 bg-[#1a2434] hover:border-white/20"}`}
    >
      <button
        onClick={onSelect}
        className="mb-5 flex items-start justify-between text-left"
      >
        <span
          className={`flex size-11 items-center justify-center rounded-xl ${model.surface} ${model.accent}`}
        >
          <model.icon size={21} />
        </span>
        <ArrowUpRight size={15} className="text-slate-500" />
      </button>
      <button onClick={onSelect} className="text-left">
        <h3 className="mb-1.5 text-lg font-semibold">{model.name}</h3>
        <p className="mb-5 text-[11px] text-slate-500">{model.caption}</p>
      </button>
      <Legend on={model.running}>
        {model.running
          ? learning
            ? "판단 · 학습 중"
            : "판단 중"
          : model.displayStatus}
      </Legend>
      <dl className="mt-4 space-y-2 text-[11px] text-slate-400">
        <div className="flex justify-between">
          <dt>가중치 업데이트</dt>
          <dd className="tabular-nums text-slate-200">
            {number(model.data.optimizer_updates)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt>모델 메모리</dt>
          <dd>
            {bytes(model.data.ram_weight_bytes ?? model.data.worker_ram_bytes)}{" "}
            /{" "}
            {bytes(
              model.data.gpu_weight_bytes ??
                (model.data.alive ? model.data.compute?.allocated_bytes : 0),
            )}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt>최근 판단</dt>
          <dd title={model.data.last_decision ?? model.data.decision?.as_of}>
            {date(model.data.last_decision ?? model.data.decision?.as_of)}
          </dd>
        </div>
      </dl>
      {model.data.error && (
        <p className="mt-3 break-words text-xs text-rose-300">
          {model.data.error}
        </p>
      )}
      {model.data.decision && (
        <p className="mt-4 text-xs text-slate-400">
          최근 판단 · {actionLabel(model.data.decision.action)} · 목표{" "}
          {percent(model.data.decision.target_weight)}
        </p>
      )}
      <AccountSummary books={model.data.books} />
      <details className="mt-5 text-xs text-slate-400">
        <summary className="cursor-pointer">판단 · 학습 · 체결 상세</summary>
        <DecisionView decision={model.data.decision} live={model.running} />
        <dl className="grid grid-cols-2 gap-3 border-y border-white/7 py-3">
          <div>
            <dt>학습 대기 경험</dt>
            <dd className="mt-1 text-slate-200">
              {number(
                model.data.replay?.remaining_for_update ??
                  model.data.replay?.untrained,
              )}
            </dd>
          </div>
          <div>
            <dt>손익 확정 대기</dt>
            <dd className="mt-1 text-slate-200">
              {number(model.data.replay?.pending)}
            </dd>
          </div>
          <div>
            <dt>최근 학습 오차</dt>
            <dd className="mt-1 text-slate-200">
              {number(model.data.learning?.loss, 6)}
            </dd>
          </div>
          <div>
            <dt>최근 학습</dt>
            <dd className="mt-1 text-slate-200">
              {date(model.data.learning?.updated_at)}
            </dd>
          </div>
        </dl>
        <h4 className="mt-4 text-xs font-medium text-slate-300">
          최근 가상 체결
        </h4>
        <FillList fills={model.data.fills} />
      </details>
      <div className="mt-6">
        <Action
          disabled={
            !model.available ||
            model.busy ||
            ["loading", "starting", "saving", "stopping"].includes(
              model.data.status ?? "",
            )
          }
          primary={!model.enabled}
          onClick={onToggle}
          className="w-full"
        >
          {model.enabled ? <Pause size={14} /> : <Play size={14} />}{" "}
          {model.busy ? "요청 중" : model.enabled ? "저장 후 정지" : "시작"}
        </Action>
        <Outcome forKey={model.role} />
      </div>
    </section>
  );
}
