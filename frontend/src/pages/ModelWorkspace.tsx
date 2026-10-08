import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  Check,
  ChartNoAxesCombined,
  FolderOpen,
  Layers3,
  LockKeyhole,
  Settings2,
  Waypoints,
} from "lucide-react";
import { useOperations } from "../data/Operations";
import { request } from "../data/api";
import type { Expert } from "../data/types";
import {
  Button,
  Drawer,
  Empty,
  ErrorMessage,
  Skeleton,
  Status,
} from "../ui/Primitives";
import { ControlButton } from "../ui/ControlButton";
import { bytes, date, number, workerState } from "../ui/format";

function expertName(e: Expert) {
  const native = e.id.match(/^macrophft_(slope|vol)_(\d)$/);
  return native
    ? `ETH ${native[1] === "slope" ? "추세" : "변동성"} 매매 ${native[2]}`
    : e.name;
}
function ExpertInspector({
  expert,
  close,
}: {
  expert: Expert | null;
  close: () => void;
}) {
  const [output, setOutput] = useState<unknown>(null),
    [error, setError] = useState("");
  useEffect(() => {
    setOutput(null);
    setError("");
    if (expert)
      void request<{ output: unknown }>(
        `experts/${encodeURIComponent(expert.id)}`,
      )
        .then((x) => setOutput(x.output))
        .catch((e) => setError(e.message));
  }, [expert?.id]);
  return (
    <Drawer
      title={expert ? expertName(expert) : "Expert"}
      open={Boolean(expert)}
      onClose={close}
    >
      {expert && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-violet-50 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-violet-700">
              <LockKeyhole size={16} />
              원본 가중치 고정
            </div>
            <p className="mt-2 text-sm leading-6 text-violet-700/70">
              {expert.id.startsWith("macrophft")
                ? "ETH 전용 원본 입력에서 매매 의견을 계산합니다."
                : expert.id.startsWith("stock_")
                  ? "원래 학습한 주식과 계좌 상태로 매매 의견을 계산합니다."
                  : "시장 시계열의 다음 관측을 예측해 MoE에 전달합니다."}
            </p>
          </div>
          {expert.error && <ErrorMessage message={expert.error} />}
          <dl className="grid grid-cols-2 gap-x-4 gap-y-5 text-sm">
            <Detail label="파라미터" value={number(expert.parameters, 0)} />
            <Detail
              label="실행 장치"
              value={expert.device ?? "아직 실행 안 됨"}
            />
            {expert.inference_seconds != null && (
              <Detail
                label="최근 분석 시간"
                value={`${number(expert.inference_seconds, 3)}s`}
              />
            )}
            <Detail label="마지막 입력" value={date(expert.last_as_of)} />
            {expert.peak_vram_bytes != null && (
              <Detail
                label="측정된 GPU peak"
                value={bytes(expert.peak_vram_bytes)}
              />
            )}
          </dl>
          {(expert.symbols ?? expert.universe)?.length ? (
            <div>
              <h3 className="mb-3 text-sm font-semibold">원래 학습한 종목</h3>
              <div className="flex flex-wrap gap-1.5">
                {(expert.symbols ?? expert.universe)!.map((s) => (
                  <span
                    key={s}
                    className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-500"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
          {error && <ErrorMessage message={error} />}
          <details className="border-t border-slate-100 pt-4">
            <summary className="cursor-pointer text-sm font-medium text-slate-500">
              출력 · 진단
            </summary>
            {output ? (
              <pre className="mt-3 max-h-96 overflow-auto rounded-xl bg-slate-950 p-4 text-[11px] leading-5 text-slate-300">
                {JSON.stringify(output, null, 2)}
              </pre>
            ) : (
              <Empty title="저장된 실제 출력이 없습니다." />
            )}
            <p className="mt-2 font-mono text-xs text-slate-400">{expert.id}</p>
          </details>
        </div>
      )}
    </Drawer>
  );
}
function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="mb-1 text-xs text-slate-400">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  );
}

export function ModelWorkspace() {
  const { state, refresh } = useOperations();
  const [experts, setExperts] = useState<Expert[]>([]),
    [inspect, setInspect] = useState<Expert | null>(null),
    [editing, setEditing] = useState(false),
    [selected, setSelected] = useState(new Set<string>()),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const close = useCallback(() => setInspect(null), []);
  useEffect(() => {
    void request<{ experts: Expert[]; selected: string[] }>("experts")
      .then((data) => {
        setExperts(data.experts);
        setSelected(
          new Set(
            data.selected.length
              ? data.selected
              : data.experts.map((e) => e.id),
          ),
        );
      })
      .catch((e) => setError(e.message));
  }, []);
  const list = state?.experts.length ? state.experts : experts;
  if (!state) return <Skeleton />;
  const running =
    state.controls.engine ||
    ["agent", "learner", "experts"].some((k) => state.workers[k]?.alive);
  const status = workerState(state.workers.agent);
  const save = async () => {
    setBusy(true);
    setError("");
    try {
      if (!selected.size) throw new Error("최소 한 개의 Expert를 선택하세요.");
      await request("settings", {
        ...state.settings,
        enabled_experts: [...selected],
      });
      setEditing(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "설정 실패");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-start justify-between gap-5 rounded-2xl bg-[#202e4a] px-6 py-6 text-white">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs text-blue-200">
            <Layers3 size={15} />
            학습된 MoE
          </div>
          <h2 className="break-all text-2xl font-bold tracking-tight">{state.settings.expert_checkpoint.split(/[\\/]/).pop()}</h2>
          <p className="mt-2 max-w-lg text-sm leading-6 text-slate-300">
            Expert {state.agent.expert_count ?? list.length}개는 고정하고,
            결합부와 Allocator를 실제 손익으로 학습합니다.
          </p>
          <div className="mt-4">
            <Status tone={status.tone} inverted>
              {status.label}
            </Status>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <ControlButton name="engine" label="MoE" />
          <Button
            onClick={() =>
              void request("model/open-directory", {}).catch((e) =>
                setError(e.message),
              )
            }
          >
            <FolderOpen size={15} />
            모델 폴더
          </Button>
        </div>
      </section>
      <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200/50">
        <div className="grid gap-3 sm:grid-cols-5">
          {[
            "시장 입력",
            "고정 Expert",
            "64D latent + 시장·계좌",
            "TorchRL Allocator",
            "목표 비중",
          ].map((label, i) => (
            <div key={label} className="flex items-center gap-3">
              <div
                className={`flex-1 rounded-xl px-3 py-3 text-center text-xs font-semibold ${i === 3 ? "bg-blue-600 text-white" : i === 1 ? "bg-violet-50 text-violet-700" : "bg-slate-50 text-slate-600"}`}
              >
                {label}
              </div>
              {i < 4 && (
                <ArrowRight
                  size={13}
                  className="hidden shrink-0 text-slate-300 sm:block"
                />
              )}
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-center gap-2 text-xs text-slate-400">
          <Waypoints size={13} />
          목표 비중을 FinRL-X StrategyResult로 전달
        </div>
      </section>
      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-bold">
            구성 Expert{" "}
            <span className="ml-2 font-normal text-slate-400">
              {selected.size} / {list.length}
            </span>
          </h2>
          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <Button onClick={() => setEditing(false)}>취소</Button>
                <Button tone="primary" busy={busy} onClick={() => void save()}>
                  구성 적용
                </Button>
              </>
            ) : (
              <Button disabled={running} onClick={() => setEditing(true)}>
                <Settings2 size={14} />
                사용 Expert 설정
              </Button>
            )}
          </div>
        </div>
        {running && (
          <p className="mb-4 text-xs text-slate-400">
            구성을 바꾸려면 MoE를 정지하세요. 현재 실행은 계속 유지됩니다.
          </p>
        )}
        {error && (
          <div className="mb-4">
            <ErrorMessage message={error} />
          </div>
        )}
        <div className="grid gap-6 lg:grid-cols-2">
          {["market", "action"].map((role) => (
            <div key={role}>
              <div className="mb-2 flex items-center gap-2 border-b border-slate-200/70 pb-3 text-xs font-semibold text-slate-500">
                <ChartNoAxesCombined size={14} />
                {role === "market" ? "시장 분석" : "매매 의견"}
              </div>
              <div className="space-y-1">
                {list
                  .filter(
                    (e) =>
                      (e.id.startsWith("stock_") || e.id.startsWith("macrophft")
                        ? "action"
                        : "market") === role,
                  )
                  .map((expert) => {
                    const included = selected.has(expert.id);
                    return (
                      <button
                        key={expert.id}
                        onClick={() =>
                          editing
                            ? setSelected((old) => {
                                const next = new Set(old);
                                next.has(expert.id)
                                  ? next.delete(expert.id)
                                  : next.add(expert.id);
                                return next;
                              })
                            : setInspect(expert)
                        }
                        className={`flex w-full items-center justify-between gap-4 rounded-xl px-3 py-3 text-left transition hover:bg-white hover:shadow-sm ${editing && included ? "bg-blue-50 ring-1 ring-blue-100" : ""}`}
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <span
                            className={`grid size-8 shrink-0 place-items-center rounded-lg ${role === "market" ? "bg-blue-100/70 text-blue-500" : "bg-violet-100/70 text-violet-500"}`}
                          >
                            {editing && included ? (
                              <Check size={16} />
                            ) : (
                              <Layers3 size={15} />
                            )}
                          </span>
                          <div className="min-w-0">
                            <div
                              className={`truncate text-sm font-semibold ${!included ? "text-slate-400" : "text-slate-700"}`}
                            >
                              {expertName(expert)}
                            </div>
                            <div className="mt-1 text-[11px] text-slate-400">
                              {["needs_input","waiting_resources"].includes(expert.status ?? "")
                                ? expert.error
                                : expert.inference_seconds != null
                                  ? `${number(expert.inference_seconds, 2)}s · ${expert.device}`
                                  : number(expert.parameters, 0) + " 파라미터"}
                            </div>
                          </div>
                        </div>
                        <Status
                          tone={
                            !included
                              ? "idle"
                              : expert.status === "error"
                                ? "bad"
                                : expert.status === "ready"
                                  ? "good"
                                  : ["needs_input","waiting_resources"].includes(expert.status ?? "")
                                    ? "warn"
                                    : "idle"
                          }
                        >
                          {!included
                            ? "제외"
                            : expert.status === "ready"
                              ? "출력 확보"
                              : expert.status === "error"
                                ? "오류"
                                : expert.status === "waiting_resources"
                                  ? "자원 대기"
                                  : expert.status === "needs_input"
                                  ? "입력 필요"
                                  : "대기"}
                        </Status>
                      </button>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      </section>
      <ExpertInspector expert={inspect} close={close} />
    </div>
  );
}
