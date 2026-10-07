import { Pause, Play } from "lucide-react";
import { useWorkspace } from "../state/Workspace";
import { Action, Outcome, Progress, QueryState } from "../components/controls";
import { EvaluationScoreboard } from "../components/EvaluationScoreboard";
import { number, stateLabel } from "../format";
export function PromotionPage() {
  const { status, assembly, command, pending,models } = useWorkspace();
  const comparison = status.data?.validation_comparison;
  const candidate = assembly.data?.candidate;
  const active = !!comparison?.active;
  const scores = comparison?.scores ?? candidate?.scores;
  return (
    <>
      <QueryState {...status} />
      <QueryState {...assembly} />
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs text-slate-500">Champion vs Candidate</p>
          <h2 className="mt-2 text-2xl font-semibold">
            {stateLabel(comparison?.status)}
          </h2>
        </div>
        <Action
          disabled={
            !candidate ||
            !!assembly.error ||
            !!pending.assembly ||
            ["loading", "saving", "stopping"].includes(
              assembly.data?.worker?.status ?? "",
            )
          }
          primary={!active}
          onClick={() =>
            void command(
              `/api/assembly/trial/${active ? "stop" : "start"}`,
              {},
              active ? "현재 평가 정지" : "현재 후보 평가 시작",
              "assembly",
            )
          }
        >
          {active ? <Pause size={16} /> : <Play size={16} />}평가{" "}
          {active ? "정지" : "시작"}
        </Action>
      </div>
      <Outcome forKey="assembly" />
      <div className="my-4 flex flex-wrap gap-3">
        <Action disabled={candidate?.evaluation_state!=='qualified'||models.some(m=>m.role!=='trading-moe'&&m.enabled)||!!pending.assembly}
          onClick={()=>void command('/api/assembly/promote',{},'Candidate 학습 가중치 승격','assembly')}>학습 가중치 승격</Action>
        {assembly.data?.last_promotion && <Action disabled={models.some(m=>m.role==='champion'&&m.enabled)||!!pending.assembly}
          onClick={()=>void command('/api/assembly/rollback',{},'이전 Champion 복원','assembly')}>이전 Champion 복원</Action>}
      </div>
      <div className="my-6">
        <div className="mb-3 flex justify-between text-xs text-slate-400">
          <span>평가 진행</span>
          <span>
            {number(comparison?.bars_current)} /{" "}
            {number(comparison?.bars_required)} 시점
          </span>
        </div>
        <Progress
          value={comparison?.bars_current}
          total={comparison?.bars_required}
          label="후보 평가 진행"
        />
      </div>
      <div className="grid gap-7 lg:grid-cols-2">
        <EvaluationScoreboard pair={scores?.replay} label="과거 데이터 평가" />
        <EvaluationScoreboard pair={scores?.paper} label="가상매매 평가" />
      </div>
      {comparison?.reason && (
        <section className="mt-7 border-l-2 border-amber-300/50 pl-4">
          <h3 className="text-sm text-amber-100">현재 판정 근거</h3>
          <p className="mt-2 text-sm text-slate-400">{comparison.reason}</p>
        </section>
      )}
      <p className="mt-7 text-xs text-slate-500">
        시험 계좌의 결과입니다. 운영 Champion·Candidate 계좌와 구분됩니다.
      </p>
    </>
  );
}
