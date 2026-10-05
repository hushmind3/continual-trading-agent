import {
  BookOpen,
  FlaskConical,
  Pause,
  Play,
  Plus,
  SkipForward,
} from "lucide-react";
import type { Assembly, Recipe } from "../../api/types";
import type { WorkspaceState } from "../../state/Workspace";
import { Action, Legend, Outcome, Switch } from "../../components/controls";

type Command = WorkspaceState["command"];
export function AssemblyControls({
  data,
  candidate,
  command,
  disabled,
  enabled,
  trialActive,
  onInspectExperts,
}: {
  data: Assembly;
  candidate?: Recipe;
  command: Command;
  disabled: boolean;
  enabled: boolean;
  trialActive: boolean;
  onInspectExperts: () => void;
}) {
  const transition = ["loading", "starting", "saving", "stopping"].includes(
    data.worker?.status ?? "",
  );
  return (
    <section className="mb-6 border-b border-white/10 pb-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <FlaskConical size={21} className="text-sky-300" />
          <Legend on={enabled}>자동조립 {enabled ? "진행 중" : "정지"}</Legend>
          <button
            onClick={onInspectExperts}
            className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-slate-400 transition-colors hover:bg-white/5 hover:text-sky-300"
          >
            <BookOpen size={14} />
            전문가 알아보기
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          <Action
            disabled={disabled}
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
            {enabled ? <Pause size={15} /> : <Play size={15} />}자동조립{" "}
            {enabled ? "정지" : "시작"}
          </Action>
          <Action
            disabled={disabled}
            onClick={() =>
              void command(
                "/api/assembly/generate",
                {},
                "새 전문가 조합 생성",
                "assembly",
              )
            }
          >
            <Plus size={15} />새 조합 만들기
          </Action>
          <Action
            disabled={disabled || !candidate || transition}
            onClick={() =>
              void command(
                `/api/assembly/trial/${trialActive ? "stop" : "start"}`,
                {},
                trialActive ? "후보 평가 정지" : "후보 평가 시작",
                "assembly",
              )
            }
          >
            {trialActive ? <Pause size={15} /> : <Play size={15} />}평가{" "}
            {trialActive ? "정지" : "시작"}
          </Action>
          <Action
            disabled={disabled || !candidate || transition}
            onClick={() =>
              void command(
                "/api/assembly/next",
                {},
                "후보 제외 후 다음 조합",
                "assembly",
              )
            }
          >
            <SkipForward size={15} />
            후보 제외 · 다음 조합
          </Action>
        </div>
      </div>
      <Outcome forKey="assembly" />
      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
        {(
          [
            ["auto_replace", "후보 자동교체"],
            ["auto_promote", "자동 승격"],
            ["detect_experts", "새 전문가 감지"],
          ] as const
        ).map(([key, label]) => (
          <label
            key={key}
            className="flex items-center gap-2.5 text-xs text-slate-400"
          >
            {label}
            <Switch
              label={label}
              on={!!data.settings?.[key]}
              disabled={disabled}
              onChange={() =>
                void command(
                  "/api/assembly/settings",
                  { [key]: !data.settings?.[key] },
                  label,
                  "assembly",
                )
              }
            />
          </label>
        ))}
      </div>
    </section>
  );
}
