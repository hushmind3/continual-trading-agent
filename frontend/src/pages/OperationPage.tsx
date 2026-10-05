import {
  ArrowDown,
  ChevronRight,
  GraduationCap,
  Radio,
  Trophy,
} from "lucide-react";
import { Legend, Switch, Outcome, QueryState } from "../components/controls";
import { useWorkspace } from "../state/Workspace";
import { ModelCard } from "../components/ModelCard";
import { ResourcePanel } from "../components/ResourcePanel";
import type { WorkspaceState } from "../state/Workspace";
type Props = Pick<
  WorkspaceState,
  | "filter"
  | "setFilter"
  | "paper"
  | "setPaper"
  | "learn"
  | "setLearn"
  | "feed"
  | "setFeed"
  | "models"
  | "selected"
  | "setSelected"
  | "toggleModel"
  | "setPage"
  | "connected"
  | "pending"
  | "command"
>;
export function OperationPage({
  filter,
  setFilter,
  paper,
  setPaper,
  learn,
  setLearn,
  feed,
  setFeed,
  models,
  selected,
  setSelected,
  toggleModel,
  setPage,
  connected,
  pending,
  command,
}: Props) {
  const { status, observe, setObserve } = useWorkspace();
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
      <div className="mb-7 flex flex-wrap items-center justify-between gap-5 border-b border-white/8 pb-5">
        <div className="flex items-center gap-1 rounded-xl bg-black/15 p-1">
          {["전체", "실행 중", "정지"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-lg px-4 py-2 text-xs font-medium transition ${filter === f ? "bg-slate-100 text-slate-900 shadow-sm" : "text-slate-500 hover:text-white"}`}
            >
              {f}
            </button>
          ))}
        </div>
        <div
          className="flex flex-wrap gap-5 text-xs text-slate-400"
          aria-label="Champion·Candidate 실행 허용 설정"
        >
          <label className="flex items-center gap-2.5">
            판단 허용
            <Switch
              label="Champion·Candidate 판단"
              disabled={!connected || !!pending.modes}
              on={observe}
              onChange={() => setObserve(!observe)}
            />
          </label>
          <label className="flex items-center gap-2.5">
            가상체결 허용
            <Switch
              label="Champion·Candidate 가상 체결"
              disabled={!connected || !!pending.modes}
              on={paper}
              onChange={() => setPaper(!paper)}
            />
          </label>
          <label className="flex items-center gap-2.5">
            학습 허용
            <Switch
              label="Champion·Candidate 학습"
              disabled={!connected || !!pending.modes}
              on={learn}
              onChange={() => setLearn(!learn)}
            />
          </label>
        </div>
      </div>
      <Outcome forKey="modes" />
      <div className="grid gap-7 xl:grid-cols-[minmax(0,1fr)_260px]">
        <section className="min-w-0">
          <div className="mb-3 flex items-center gap-4 rounded-2xl border border-white/8 bg-[#192333] p-5">
            <div
              className={`flex size-11 shrink-0 items-center justify-center rounded-full ${feed ? "bg-emerald-400/12 text-emerald-300" : "bg-slate-700 text-slate-400"}`}
            >
              <Radio size={22} />
            </div>
            <div className="flex-1">
              <h2 className="text-sm font-semibold">시장 데이터</h2>
              <div className="mt-2">
                <Legend on={feed}>
                  {!connected ? "상태 미수신" : feed ? "수신 중" : "수신 정지"}
                </Legend>
              </div>
            </div>
            <button
              onClick={() => {
                setFeed(!feed);
              }}
              disabled={!connected || !!pending.feed}
              className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 transition hover:border-sky-300/50 hover:text-sky-300"
            >
              {pending.feed
                ? "요청 중"
                : feed
                  ? "시세·운영모델 정지"
                  : "시세 시작"}
            </button>
            {feed && (
              <button
                disabled={!!pending.feed}
                onClick={() =>
                  void command("/api/feed/reconnect", {}, "시세 재연결", "feed")
                }
                className="px-3 text-xs text-sky-300 disabled:opacity-40"
              >
                재연결
              </button>
            )}
          </div>
          <Outcome forKey="feed" />
          <div className="mb-3 flex justify-center text-slate-600">
            <ArrowDown size={19} />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {visibleModels.map((model) => (
              <ModelCard
                key={model.name}
                model={model}
                selected={selected === model.name}
                learning={model.running && !!model.data.learning_active}
                onSelect={() => setSelected(model.name)}
                onToggle={() => toggleModel(model.name)}
              />
            ))}
          </div>
          {visibleModels.length === 0 && (
            <div className="py-16 text-center text-sm text-slate-500">
              해당 상태의 모델이 없습니다.
            </div>
          )}
          <div className="mt-7 grid gap-4 sm:grid-cols-2">
            <button
              onClick={() => {
                setPage(4);
                setSelected(null);
              }}
              className="group flex items-center gap-4 rounded-2xl bg-violet-400/8 p-5 text-left transition hover:bg-violet-400/14"
            >
              <GraduationCap size={25} className="text-violet-300" />
              <div className="flex-1">
                <h3 className="text-sm font-medium text-violet-100">
                  학습 모니터
                </h3>
                <p className="mt-1.5 text-xs text-slate-500">
                  경험 처리와 업데이트 확인
                </p>
              </div>
              <ChevronRight
                size={17}
                className="text-violet-300 transition group-hover:translate-x-1"
              />
            </button>
            <button
              onClick={() => setPage(5)}
              className="group flex items-center gap-4 rounded-2xl bg-amber-300/8 p-5 text-left transition hover:bg-amber-300/14"
            >
              <Trophy size={25} className="text-amber-200" />
              <div className="flex-1">
                <h3 className="text-sm font-medium text-amber-100">
                  승급 평가
                </h3>
                <p className="mt-1.5 text-xs text-slate-500">
                  Champion · Candidate 비교
                </p>
              </div>
              <ChevronRight
                size={17}
                className="text-amber-200 transition group-hover:translate-x-1"
              />
            </button>
          </div>
        </section>
        <ResourcePanel onDetails={() => setPage(8)} />
      </div>
    </>
  );
}
