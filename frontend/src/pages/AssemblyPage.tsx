import { useWorkspace } from "../state/Workspace";
import {
  Action,
  Empty,
  Outcome,
  QueryState,
  Switch,
} from "../components/controls";
import { date, number, stateLabel } from "../format";
export function AssemblyPage() {
  const { assembly, command, pending } = useWorkspace();
  const data = assembly.data;
  const candidate = data?.candidate;
  const enabled = !!data?.enabled;
  const trialActive = !!data?.worker?.alive;
  const unavailable = !data || !!assembly.error || !!pending.assembly;
  return (
    <>
      <QueryState {...assembly} />
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">
            자동실험 {enabled ? "진행 중" : "정지"}
          </h2>
          <p className="mt-2 text-xs text-slate-500">
            시험 {number(data?.experiments)} · 승격 {number(data?.promotions)} ·
            탈락 {number(data?.rejections)}
          </p>
        </div>
        <Action
          disabled={unavailable}
          primary={!enabled}
          onClick={() =>
            void command(
              `/api/assembly/${enabled ? "stop" : "start"}`,
              {},
              enabled ? "자동조립 정지" : "자동조립 시작",
              "assembly",
            )
          }
        >
          자동조립 {enabled ? "정지" : "시작"}
        </Action>
      </div>
      <Outcome forKey="assembly" />
      <section className="mt-6 grid gap-5 md:grid-cols-[1fr_40px_1.3fr]">
        <div className="border-t-2 border-sky-400/50 pt-4">
          <p className="mb-3 text-xs text-slate-500">현재 기준 · Champion</p>
          <h3 className="break-all text-sm font-medium">
            {data?.champion?.candidate_id ?? "구성 미수신"}
          </h3>
          <p className="mt-3 text-xs text-slate-400">
            전문가 {number(data?.champion?.enabled_experts?.length)}개
          </p>
        </div>
        <span className="self-center text-center text-slate-500">→</span>
        <div className="rounded-2xl bg-violet-400/8 p-5">
          <p className="mb-3 text-xs text-violet-300">
            현재 후보 · {stateLabel(candidate?.evaluation_state)}
          </p>
          <h3 className="break-all text-sm font-medium">
            {candidate?.candidate_id ?? "후보 없음"}
          </h3>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            {candidate?.mutation_description ?? "변경 내용 없음"}
          </p>
          {candidate?.reason && (
            <p className="mt-3 text-xs text-slate-500">{candidate.reason}</p>
          )}
        </div>
      </section>
      <div className="my-6 flex flex-wrap gap-3">
        <Action
          disabled={unavailable}
          onClick={() =>
            void command(
              "/api/assembly/generate",
              {},
              "새 후보 생성",
              "assembly",
            )
          }
        >
          새 후보 생성
        </Action>
        <Action
          disabled={unavailable || !candidate}
          onClick={() =>
            void command(
              `/api/assembly/trial/${trialActive ? "stop" : "start"}`,
              {},
              trialActive ? "후보 시험 정지" : "후보 시험 시작",
              "assembly",
            )
          }
        >
          현재 후보 시험 {trialActive ? "정지" : "시작"}
        </Action>
        <Action
          disabled={unavailable || !candidate}
          onClick={() =>
            void command(
              "/api/assembly/next",
              {},
              "현재 후보 탈락 후 다음 후보",
              "assembly",
            )
          }
        >
          탈락 · 다음 후보
        </Action>
      </div>
      <div className="flex flex-wrap gap-5 border-y border-white/10 py-5">
        {(
          [
            ["auto_replace", "후보 자동교체"],
            ["auto_promote", "자동 승격"],
            ["detect_experts", "새 전문가 감지"],
          ] as const
        ).map(([key, label]) => (
          <label
            key={key}
            className="flex items-center gap-3 text-xs text-slate-400"
          >
            {label}
            <Switch
              label={label}
              on={!!data?.settings?.[key]}
              disabled={unavailable}
              onChange={() =>
                void command(
                  "/api/assembly/settings",
                  { [key]: !data?.settings?.[key] },
                  label,
                  "assembly",
                )
              }
            />
          </label>
        ))}
      </div>
      <details className="mt-6">
        <summary className="cursor-pointer text-sm text-slate-300">
          전문가 구성 비교 · 새 전문가 {number(data?.new_experts?.length)}
        </summary>
        <div className="mt-4 overflow-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-slate-500">
                {["전문가", "역할", "Champion", "Candidate", "갱신"].map(
                  (label) => (
                    <th key={label} className="py-3 font-normal">
                      {label}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {data?.experts?.map((expert) => (
                <tr key={expert.id} className="border-t border-white/5">
                  <td className="py-3">
                    {expert.name}
                    {data.new_experts?.includes(expert.id) && (
                      <span className="ml-2 text-teal-300">신규</span>
                    )}
                  </td>
                  <td>{expert.role}</td>
                  <td>
                    {data.champion?.enabled_experts?.includes(expert.id)
                      ? "사용"
                      : "제외"}
                  </td>
                  <td>
                    {candidate?.enabled_experts?.includes(expert.id)
                      ? "사용"
                      : "제외"}
                  </td>
                  <td>
                    {candidate?.refresh_seconds?.[expert.id] === undefined
                      ? "설정 없음"
                      : `${number(candidate.refresh_seconds[expert.id])}초`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        <section>
          <h2 className="mb-4 text-sm font-semibold">
            대기 후보 · {number(data?.queue?.length)}
          </h2>
          {data?.queue?.length ? (
            data.queue.map((recipe) => (
              <div
                key={recipe.candidate_id}
                className="border-t border-white/5 py-4"
              >
                <p className="break-all text-xs text-slate-300">
                  {recipe.candidate_id}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  {recipe.mutation_description}
                </p>
              </div>
            ))
          ) : (
            <Empty>대기 후보가 없습니다.</Empty>
          )}
        </section>
        <section>
          <h2 className="mb-4 text-sm font-semibold">최근 실험 기록</h2>
          {data?.history?.length ? (
            data.history.slice(0, 20).map((entry, index) => (
              <div
                key={`${entry.time}-${index}`}
                className="border-t border-white/5 py-4 text-xs"
              >
                <p className="text-slate-300">
                  {stateLabel(entry.event)} · {entry.candidate_id}
                </p>
                <p className="mt-2 text-slate-500">
                  {entry.reason ?? entry.mutation} · {date(entry.time)}
                </p>
              </div>
            ))
          ) : (
            <Empty>실험 기록이 없습니다.</Empty>
          )}
        </section>
      </div>
    </>
  );
}
