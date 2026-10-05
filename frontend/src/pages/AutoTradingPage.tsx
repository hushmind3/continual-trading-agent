import { ChevronRight, GraduationCap, Trophy } from "lucide-react";
import { ModelCard } from "../components/ModelCard";
import { Empty, QueryState } from "../components/controls";
import { useWorkspace } from "../state/Workspace";

export function AutoTradingPage() {
  const {
    status,
    moe,
    models,
    filter,
    setFilter,
    selected,
    setSelected,
    toggleModel,
    setPage,
  } = useWorkspace();
  const visibleModels = models.filter(
    (model) =>
      filter === "전체" ||
      (filter === "실행 중"
        ? model.running
        : model.available && !model.enabled),
  );
  return (
    <>
      <QueryState {...status} />
      <QueryState {...moe} />
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div
          className="flex items-center gap-1 rounded-xl bg-black/15 p-1"
          aria-label="자동매매 모델 필터"
        >
          {["전체", "실행 중", "정지"].map((value) => (
            <button
              key={value}
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
              className={`rounded-lg px-4 py-2 text-xs font-medium transition-colors ${filter === value ? "bg-slate-100 text-slate-900 shadow-sm" : "text-slate-500 hover:text-white"}`}
            >
              {value}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500">
          Champion · Candidate · TradingMoE
        </p>
      </div>
      <div className="grid items-start gap-4 md:grid-cols-3">
        {visibleModels.map((model) => (
          <ModelCard
            key={model.role}
            model={model}
            selected={selected === model.name}
            learning={model.running && !!model.data.learning_active}
            onSelect={() => setSelected(model.name)}
            onToggle={() => toggleModel(model.name)}
          />
        ))}
      </div>
      {!visibleModels.length && <Empty>해당 상태의 모델이 없습니다.</Empty>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <button
          onClick={() => {
            setPage(3);
            setSelected(null);
          }}
          className="group flex items-center gap-4 rounded-2xl bg-violet-400/8 p-4 text-left transition-colors hover:bg-violet-400/14"
        >
          <GraduationCap size={23} className="text-violet-300" />
          <div className="flex-1">
            <h2 className="text-sm font-medium text-violet-100">학습 모니터</h2>
            <p className="mt-1 text-xs text-slate-500">
              경험 처리와 가중치 업데이트
            </p>
          </div>
          <ChevronRight
            size={16}
            className="text-violet-300 transition-transform group-hover:translate-x-1"
          />
        </button>
        <button
          onClick={() => setPage(4)}
          className="group flex items-center gap-4 rounded-2xl bg-amber-300/8 p-4 text-left transition-colors hover:bg-amber-300/14"
        >
          <Trophy size={23} className="text-amber-200" />
          <div className="flex-1">
            <h2 className="text-sm font-medium text-amber-100">승급 평가</h2>
            <p className="mt-1 text-xs text-slate-500">
              Champion · Candidate 비교
            </p>
          </div>
          <ChevronRight
            size={16}
            className="text-amber-200 transition-transform group-hover:translate-x-1"
          />
        </button>
      </div>
    </>
  );
}
