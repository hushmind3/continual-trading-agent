import { useWorkspace } from "../state/Workspace";
import { Action, Empty, Outcome, QueryState } from "../components/controls";
import { ResourcePanel } from "../components/ResourcePanel";
import { bytes, date, number } from "../format";
export function SystemPage() {
  const {
    status,
    models,
    moe,
    assembly,
    registry,
    provider,
    command,
    pending,
  } = useWorkspace();
  const logs = status.data?.logs;
  const lines = Array.isArray(logs)
    ? logs
    : (logs?.split("\n").filter(Boolean) ?? []);
  return (
    <>
      <QueryState {...status} />
      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_260px]">
        <div>
          <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
            <p className="text-xs text-slate-500">
              최근 수신 {date(status.data?.status_updated_at)}
            </p>
            <Action
              disabled={!!pending.server}
              onClick={() =>
                void command(
                  "/api/server/restart",
                  {},
                  "웹서버 재시작",
                  "server",
                )
              }
            >
              웹서버만 재시작
            </Action>
          </div>
          <Outcome forKey="server" />
          {models.map((model) => (
            <section
              key={model.role}
              className="mb-6 border-t border-white/10 pt-4"
            >
              <h2 className="mb-4 text-sm font-semibold">
                {model.name} · {model.displayStatus}
              </h2>
              <dl className="grid gap-3 text-xs sm:grid-cols-2">
                <div>
                  PID {model.running ? number(model.data.pid) : "미실행"}
                </div>
                <div>
                  적재{" "}
                  {model.data.loaded === undefined
                    ? "상태 미수신"
                    : model.data.loaded
                      ? "예"
                      : "아니요"}
                </div>
                <div>
                  RAM{" "}
                  {bytes(
                    model.data.ram_weight_bytes ?? model.data.worker_ram_bytes,
                  )}
                </div>
                <div>
                  VRAM{" "}
                  {bytes(
                    model.data.gpu_weight_bytes ??
                      (model.running ? model.data.compute?.allocated_bytes : 0),
                  )}
                </div>
                <div className="break-all sm:col-span-2">
                  모델 파일 {model.data.checkpoint ?? "미수신"}
                </div>
              </dl>
              {model.data.expert_status && <details className="mt-4 text-xs">
                <summary className="cursor-pointer text-sky-300">전문가 실행 상태</summary>
                <ul className="mt-3 space-y-2">{Object.entries(model.data.expert_status).map(([id,execution])=><li key={id} className="border-b border-white/8 py-2">
                  <div className="flex justify-between gap-3"><span>{registry.data?.experts?.find(e=>e.id===id)?.name??id}</span>
                    <span className={execution.status==='executed'?'text-emerald-300':'text-amber-300'}>{execution.status==='executed'?'실행됨':execution.status==='disabled'?'구성 제외':'입력 대기'}</span></div>
                  {execution.reason&&<p className="mt-1 break-words text-slate-500">{execution.reason}</p>}
                  {execution.as_of&&<p className="mt-1 text-slate-500">입력 시각 {date(execution.as_of)}</p>}
                  {execution.news_status==='native_missing_news_neutral_3'&&<p className="mt-1 text-slate-500">뉴스 미수신 · 원본 정책의 중립값 적용</p>}
                </li>)}</ul></details>}
              {model.data.error && (
                <p className="mt-3 break-words text-xs text-rose-300">
                  {model.data.error}
                </p>
              )}
            </section>
          ))}
          <h2 className="mb-4 text-sm font-semibold">서버 로그</h2>
          {lines.length ? (
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-black/15 p-4 text-xs text-slate-400">
              {lines.slice(-100).join("\n")}
            </pre>
          ) : (
            <Empty>서버 로그가 없습니다.</Empty>
          )}
          <div className="mt-6 space-y-3">
            {[
              ["운영 상태", status.data],
              ["TradingMoE", moe.data],
              ["자동실험", assembly.data],
              ["전문가 목록", registry.data],
              ["연결 상태", provider.data],
            ].map(([name, data]) => (
              <details key={String(name)} className="text-xs text-slate-500">
                <summary className="cursor-pointer py-2">
                  {String(name)} · 원본 진단
                </summary>
                <pre className="max-h-96 overflow-auto whitespace-pre-wrap bg-black/15 p-4 text-[11px]">
                  {JSON.stringify(data, null, 2) ?? "미수신"}
                </pre>
              </details>
            ))}
          </div>
        </div>
        <ResourcePanel
          onDetails={() => window.scrollTo({ top: 0, behavior: "smooth" })}
        />
      </div>
    </>
  );
}
