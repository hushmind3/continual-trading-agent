import { ArrowRight, Check, FlaskConical } from "lucide-react";
import type { Assembly, Expert } from "../../api/types";
import { Empty } from "../../components/controls";
import { EvaluationScoreboard } from "../../components/EvaluationScoreboard";
import {
  candidateChanges,
  number,
  percent,
  pnlColor,
  stateLabel,
  symbolName,
} from "../../format";

export function AssemblyOverview({
  data,
  experts,
}: {
  data: Assembly;
  experts: Expert[];
}) {
  const candidate = data.candidate;
  if (!candidate)
    return <Empty>조립된 후보의 평가 상태가 여기에 표시됩니다.</Empty>;
  const state = data.worker?.alive
    ? (data.worker.evaluation_stage ?? candidate.evaluation_state)
    : candidate.evaluation_state;
  const stage =
    state === "promoted" || state === "rejected"
      ? 3
      : ["ready", "replay", "paper"].indexOf(state ?? "");
  const pair = candidate.scores?.paper ?? candidate.scores?.replay;
  return (
    <section
      aria-label="현재 조합 평가"
      className="rounded-2xl bg-violet-400/8 p-4"
    >
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <FlaskConical size={17} className="text-violet-300" />
        후보 평가
      </h2>
      <p
        className={`mt-3 text-xl font-semibold ${state === "rejected" || state === "error" ? "text-rose-300" : state === "promoted" ? "text-teal-300" : "text-violet-200"}`}
      >
        {stateLabel(state)}
      </p>
      {data.evaluation_context?.symbols?.length ? (
        <p className="mt-2 text-xs text-slate-400">
          시험 대상{" "}
          <span className="text-slate-200">
            {data.evaluation_context.symbols
              .map((symbol) => symbolName(symbol))
              .join(" · ")}
          </span>
        </p>
      ) : null}
      <ol aria-label="후보 평가 단계" className="mt-5 grid grid-cols-4 gap-1">
        {["조합", "과거 평가", "가상 평가", "판정"].map((label, index) => {
          const done = stage > index || (index === 0 && stage < 0);
          const current = stage === index;
          return (
            <li
              key={label}
              className={`text-center text-[10px] ${current ? "text-violet-200" : done ? "text-sky-300" : "text-slate-500"}`}
            >
              <div
                className={`mb-2 flex h-6 items-center justify-center rounded-md ${current ? "bg-violet-400/20" : done ? "bg-sky-400/10" : "bg-white/5"}`}
              >
                {done ? <Check size={12} /> : index + 1}
              </div>
              {label}
            </li>
          );
        })}
      </ol>
      {candidate.reason && (
        <p className="mt-3 text-xs leading-5 text-slate-400">
          {candidate.reason}
        </p>
      )}
      {data.worker?.error && (
        <p role="alert" className="mt-3 text-xs text-rose-300">
          {data.worker.error}
        </p>
      )}
      <div className="mt-5 border-t border-white/10 pt-4">
        <h3 className="text-xs font-medium text-slate-400">
          이번 조합의 변경점
        </h3>
        <ul className="mt-2 space-y-2 text-sm text-slate-200">
          {candidateChanges(candidate, experts).map((change, index) => (
            <li key={index} className="flex items-start gap-2">
              <ArrowRight size={14} className="mt-1 shrink-0 text-violet-300" />
              {change}
            </li>
          ))}
        </ul>
      </div>
      {pair && (
        <div className="mt-4 flex items-center justify-between gap-3 border-t border-white/10 pt-3 text-xs">
          <span className="text-slate-400">Champion 대비 수익률</span>
          <strong className={pnlColor(pair.delta)}>
            {pair.delta === undefined
              ? "비교 대기"
              : `${number(pair.delta * 100, 3)}%p`}
          </strong>
        </div>
      )}
      {pair?.candidate?.max_drawdown !== undefined && (
        <p className="mt-2 text-xs text-slate-400">
          최대 손실폭 {percent(pair.candidate.max_drawdown)} · 체결{" "}
          {number(pair.candidate.trades)}회
        </p>
      )}
      {candidate.scores && Object.keys(candidate.scores).length > 0 && (
        <details className="mt-4 text-xs">
          <summary className="cursor-pointer text-slate-400">
            평가 성적 비교
          </summary>
          <EvaluationScoreboard
            pair={candidate.scores.replay}
            label="과거 데이터 평가"
          />
          <EvaluationScoreboard
            pair={candidate.scores.paper}
            label="가상매매 평가"
          />
        </details>
      )}
      <details className="mt-4 border-t border-white/10 pt-3 text-xs text-slate-500">
        <summary className="cursor-pointer">구성 식별 정보</summary>
        <dl className="mt-2 space-y-2 break-all">
          <div>
            <dt>후보</dt>
            <dd>{candidate.candidate_id}</dd>
          </div>
          <div>
            <dt>부모 구성</dt>
            <dd>{candidate.parent_id}</dd>
          </div>
        </dl>
      </details>
    </section>
  );
}
