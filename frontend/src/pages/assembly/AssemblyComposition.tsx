import {
  BrainCircuit,
  ChartNoAxesCombined,
  ChevronRight,
  Layers,
} from "lucide-react";
import type { Expert, Recipe } from "../../api/types";
import { Empty } from "../../components/controls";
import { expertName, expertUniverse, number } from "../../format";

export function AssemblyComposition({
  experts,
  candidate,
  newExperts,
  onInspect,
}: {
  experts: Expert[];
  candidate?: Recipe;
  newExperts: string[];
  onInspect: (id: string) => void;
}) {
  const included = candidate
    ? experts.filter((expert) => candidate.enabled_experts?.includes(expert.id))
    : experts.filter((expert) => expert.eligible);
  const excluded = candidate
    ? experts.filter(
        (expert) => !candidate.enabled_experts?.includes(expert.id),
      )
    : [];
  return (
    <section aria-label="TradingMoE 조립 작업대">
      <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Layers size={20} className="text-sky-300" />
            {candidate ? "현재 TradingMoE 조합" : "TradingMoE 조립 재료"}
          </h2>
          <p className="mt-1.5 text-xs text-slate-400">
            {candidate
              ? `전문가 ${number(candidate.enabled_experts?.length)}개의 분석·매매 의견을 결합하는 구성`
              : "새 조합을 만들면 등록된 전문가를 조합해 후보를 생성합니다."}
          </p>
        </div>
        <p className="pt-1 text-xs text-slate-500">
          조립 가능 {number(experts.filter((expert) => expert.eligible).length)}{" "}
          / {number(experts.length)}
          {newExperts.length > 0 ? ` · 신규 ${number(newExperts.length)}` : ""}
        </p>
      </header>
      <div className="grid items-start gap-5 sm:grid-cols-2">
        {(
          [
            {
              role: "market",
              title: "시장 분석",
              caption: "가격과 시장 흐름을 분석",
              icon: ChartNoAxesCombined,
              color: "text-sky-300",
              surface: "bg-sky-400/8",
            },
            {
              role: "policy",
              title: "매매 판단",
              caption: "매매 행동에 대한 의견을 제시",
              icon: BrainCircuit,
              color: "text-violet-300",
              surface: "bg-violet-400/8",
            },
          ] as const
        ).map((group) => {
          const members = included.filter(
            (expert) => expert.role === group.role,
          );
          const routing =
            group.role === "market"
              ? candidate?.market_routing
              : candidate?.policy_routing;
          return (
            <section
              key={group.role}
              className={`min-w-0 rounded-xl ${group.surface} p-3`}
            >
              <header className="mb-3 flex items-center justify-between gap-3">
                <h3
                  className={`flex items-center gap-2 text-sm font-medium ${group.color}`}
                >
                  <group.icon size={16} />
                  {group.title}
                </h3>
                <span className="text-xs text-slate-400">
                  {number(members.length)}개
                </span>
              </header>
              <p className="mb-2 text-[11px] text-slate-500">{group.caption}</p>
              <ul>
                {members.map((expert) => (
                  <li key={expert.id}>
                    <button
                      onClick={() => onInspect(expert.id)}
                      aria-label={`${expertName(expert)} 역할 보기`}
                      className="group flex w-full min-w-0 items-center gap-2 rounded-lg px-2 py-2 text-left transition-colors hover:bg-white/7 focus-visible:outline-2 focus-visible:outline-sky-400"
                    >
                      <span className="min-w-0 truncate text-xs text-slate-200">
                        {expertName(expert)}
                      </span>
                      <span className="shrink-0 text-[10px] text-slate-500">
                        {expertUniverse(expert)}
                        {newExperts.includes(expert.id) ? " · 신규" : ""}
                      </span>
                      <ChevronRight
                        size={13}
                        className="ml-auto shrink-0 text-slate-600 transition-transform group-hover:translate-x-0.5 group-hover:text-slate-300"
                      />
                    </button>
                  </li>
                ))}
              </ul>
              {!members.length && <Empty>아직 포함된 전문가가 없습니다.</Empty>}
              {routing && (
                <p className="mt-3 border-t border-white/7 pt-3 text-[10px] leading-5 text-slate-400">
                  {routing.top_k === undefined
                    ? null
                    : routing.top_k === 0
                      ? "전문가 개수 제한 없이 의견 반영"
                      : `한 판단에 최대 ${number(routing.top_k)}개 의견 반영`}
                  {routing.temperature === undefined
                    ? null
                    : ` · 선택 다양성 ${number(routing.temperature, 2)}`}
                </p>
              )}
            </section>
          );
        })}
      </div>
      {excluded.length > 0 && (
        <details className="mt-4 text-xs">
          <summary className="cursor-pointer text-slate-500">
            현재 조합에서 제외된 전문가 {number(excluded.length)}개
          </summary>
          <div className="mt-2 flex flex-wrap gap-2">
            {excluded.map((expert) => (
              <button
                key={expert.id}
                onClick={() => onInspect(expert.id)}
                className="rounded-lg bg-white/5 px-3 py-2 text-slate-400 hover:text-sky-300"
              >
                {expertName(expert)}
              </button>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}
