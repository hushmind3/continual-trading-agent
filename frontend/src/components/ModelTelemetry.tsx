import { Database, RefreshCw } from "lucide-react";
import type { RuntimeModel } from "../state/Workspace";
import { bytes, date, number } from "../format";
import { Legend } from "./controls";

export function ModelTelemetry({ models }: { models: RuntimeModel[] }) {
  return (
    <section aria-label="전체 모델 처리 상태" className="mt-6">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">전체 모델 처리 상태</h2>
        <span className="text-[11px] text-slate-500">
          입력 → 캐시 → 학습 경험 → 가중치 업데이트
        </span>
      </header>
      <div className="divide-y divide-white/8 rounded-xl border border-white/8 bg-white/2 px-4">
        {models.map((model) => {
          const { data } = model;
          const cache = data.cache;
          const replay = data.replay;
          const learning = model.running && !!data.learning_active;
          return (
            <article
              key={model.role}
              aria-label={`${model.name} 처리 상태`}
              className="grid grid-cols-2 items-start gap-4 py-4 lg:grid-cols-[8rem_repeat(3,minmax(0,1fr))]"
            >
              <div className="col-span-2 lg:col-span-1">
                <h3 className={`mb-2 text-sm font-semibold ${model.accent}`}>
                  {model.name}
                </h3>
                <Legend on={model.running}>{model.displayStatus}</Legend>
                <p
                  className="mt-2 text-[10px] leading-4 text-slate-500"
                  title={data.last_decision ?? data.decision?.as_of}
                >
                  {data.source_kind === "historical_paper"
                    ? "과거 시세 입력"
                    : "최근 판단"}
                  <br />
                  {date(data.last_decision ?? data.decision?.as_of)}
                </p>
              </div>
              <div>
                <h4 className="mb-2 flex items-center gap-1.5 text-[11px] text-slate-500">
                  <Database size={12} />
                  전문가 캐시
                </h4>
                {cache?.available ? (
                  <>
                    <p className="text-lg font-semibold tabular-nums">
                      {number(cache.market_outputs)}
                      <span className="ml-1 text-[11px] font-normal text-slate-400">
                        출력
                      </span>
                    </p>
                    <p className="mt-1 text-[10px] text-slate-400">
                      보관 판단 {number(cache.stored_decisions)} ·{" "}
                      {bytes(cache.bytes)}
                    </p>
                    <p className="mt-1 text-[10px] text-slate-500">
                      저장 구간 {number(cache.cycles)}개
                    </p>
                  </>
                ) : (
                  <p className="text-xs text-slate-400">
                    {cache?.error ? "캐시 조회 실패" : "캐시 기록 없음"}
                  </p>
                )}
              </div>
              <div>
                <h4 className="mb-2 text-[11px] text-slate-500">학습 경험</h4>
                <p
                  className="text-lg font-semibold tabular-nums"
                  aria-label={`${model.name} 학습 대기`}
                >
                  {number(replay?.remaining_for_update ?? replay?.untrained)}
                  <span className="ml-1 text-[11px] font-normal text-slate-400">
                    대기
                  </span>
                </p>
                <p className="mt-1 text-[10px] text-slate-400">
                  손익 확정 대기 {number(replay?.pending)}
                </p>
                <p className="mt-1 text-[10px] text-slate-500">
                  저장 {number(replay?.total)} · 학습 가능{" "}
                  {number(replay?.eligible)}
                </p>
                {!!replay?.quarantined && (
                  <p className="mt-1 text-[10px] text-amber-300">
                    분리 보관 {number(replay.quarantined)}
                  </p>
                )}
                {replay?.storage_pressure && (
                  <p role="alert" className="mt-1 text-[10px] text-rose-300">
                    경험 저장소 용량 주의
                  </p>
                )}
              </div>
              <div className="col-span-2 lg:col-span-1">
                <h4 className="mb-2 flex items-center gap-1.5 text-[11px] text-slate-500">
                  <RefreshCw
                    size={12}
                    className={learning ? "animate-spin text-teal-300" : ""}
                  />
                  가중치 업데이트
                </h4>
                <div className="flex items-baseline gap-2">
                  <output
                    aria-label={`${model.name} 가중치 업데이트`}
                    className="text-xl font-semibold tabular-nums"
                  >
                    {number(data.optimizer_updates)}
                  </output>
                  <span
                    className={`text-[10px] ${learning ? "text-teal-300" : "text-slate-500"}`}
                  >
                    {learning
                      ? "학습 중"
                      : model.running
                        ? "학습 대기"
                        : "정지"}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-slate-400">
                  최근 오차 {number(data.learning?.loss, 6)}
                </p>
                <p
                  className="mt-1 text-[10px] text-slate-500"
                  title={data.learning?.updated_at}
                >
                  {date(data.learning?.updated_at)}
                </p>
              </div>
              {data.error && (
                <p
                  role="alert"
                  className="col-span-full break-words text-xs text-rose-300"
                >
                  {data.error}
                </p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
