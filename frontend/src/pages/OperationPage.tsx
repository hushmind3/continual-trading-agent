import { BrainCircuit, ChevronRight, Radio } from "lucide-react";
import {
  Action,
  Legend,
  Outcome,
  QueryState,
  Switch,
} from "../components/controls";
import { ResourcePanel } from "../components/ResourcePanel";
import { ModelTelemetry } from "../components/ModelTelemetry";
import { date, number } from "../format";
import { useWorkspace } from "../state/Workspace";

export function OperationPage() {
  const {
    status,
    moe,
    assembly,
    models,
    connected,
    observe,
    setObserve,
    paper,
    setPaper,
    learn,
    setLearn,
    feed,
    setFeed,
    pending,
    command,
    setPage,
  } = useWorkspace();
  const freshness = status.data?.feed_metrics?.fresh_symbols_5m;
  return (
    <>
      <QueryState {...status} />
      <QueryState {...moe} />
      <section className="mb-6 border-b border-white/8 pb-5">
        <h2 className="mb-4 text-sm font-semibold">
          운영 모드{" "}
          <span className="ml-2 text-xs font-normal text-slate-500">
            Champion · Candidate 허용 설정
          </span>
        </h2>
        <div
          className="flex flex-wrap gap-x-6 gap-y-4 text-xs text-slate-400"
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
        <Outcome forKey="modes" />
      </section>
      <div className="grid items-start gap-7 xl:grid-cols-[minmax(0,1fr)_260px]">
        <section className="min-w-0">
          <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-white/8 bg-[#192333] p-5">
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
            <Action
              disabled={!connected || !!pending.feed}
              onClick={() => setFeed(!feed)}
            >
              {pending.feed
                ? "요청 중"
                : feed
                  ? "시세·Champion·Candidate 정지"
                  : "시세 시작"}
            </Action>
            {feed && (
              <Action
                disabled={!!pending.feed}
                onClick={() =>
                  void command("/api/feed/reconnect", {}, "시세 재연결", "feed")
                }
              >
                재연결
              </Action>
            )}
          </div>
          <Outcome forKey="feed" />
          <dl className="mt-5 flex flex-wrap gap-x-10 gap-y-4 text-xs">
            <div>
              <dt className="text-slate-500">수집 대상</dt>
              <dd className="mt-2 text-lg tabular-nums">
                {number(status.data?.configured_instruments)}종목
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">최근 5분 수신</dt>
              <dd className="mt-2 text-lg tabular-nums">
                {number(
                  Array.isArray(freshness) ? freshness.length : undefined,
                )}
                종목
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">저장된 시세</dt>
              <dd className="mt-2 text-lg tabular-nums">
                {number(status.data?.feed_rows)}행
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">최근 상태 갱신</dt>
              <dd className="mt-2 text-lg tabular-nums">
                {date(status.data?.status_updated_at)}
              </dd>
            </div>
          </dl>
          <ModelTelemetry models={models} />
          <div className="mt-4 flex flex-wrap gap-x-7 gap-y-3 text-xs">
            <button
              onClick={() => setPage(5)}
              className="text-slate-400 hover:text-sky-300"
            >
              조립 자동화 ·{" "}
              {assembly.error
                ? "연결 확인 필요"
                : !assembly.data
                  ? "확인 중"
                  : assembly.data.enabled
                    ? "실행 중"
                    : "정지"}
            </button>
            <button
              onClick={() => setPage(4)}
              className="text-slate-400 hover:text-amber-200"
            >
              승급 평가 ·{" "}
              {status.data?.validation_comparison?.active ? "평가 중" : "대기"}
            </button>
          </div>
          <button
            onClick={() => setPage(1)}
            className="mt-7 flex w-full items-center gap-4 rounded-xl bg-sky-400/8 p-4 text-left transition-colors hover:bg-sky-400/12"
          >
            <BrainCircuit size={23} className="text-sky-300" />
            <div className="flex-1">
              <h2 className="text-sm font-medium text-sky-200">
                자동매매 열기
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                세 모델의 실행 제어·가상계좌·학습 상태
              </p>
            </div>
            <ChevronRight size={16} className="text-sky-300" />
          </button>
        </section>
        <ResourcePanel onDetails={() => setPage(7)} />
      </div>
    </>
  );
}
