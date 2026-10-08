import {
  ArrowRight,
  Boxes,
  CheckCircle2,
  Cpu,
  Database,
  GraduationCap,
  Radio,
  ShieldCheck,
} from "lucide-react";
import { useOperations } from "../data/Operations";
import { ControlButton } from "../ui/ControlButton";
import { Empty, Meter, Skeleton, Status } from "../ui/Primitives";
import {accountNames,bytes,date,money,number,workerState} from "../ui/format";

const steps = [
  { role: "feed", label: "시장 입력", icon: Radio, color: "text-blue-500" },
  {
    role: "experts",
    label: "Expert 분석",
    icon: Boxes,
    color: "text-violet-500",
  },
  {
    role: "agent",
    label: "MoE 판단 · 체결",
    icon: ShieldCheck,
    color: "text-emerald-500",
  },
  {
    role: "learner",
    label: "지속 학습",
    icon: GraduationCap,
    color: "text-amber-500",
  },
];

export function OperationsBoard() {
  const { state } = useOperations();
  if (!state) return <Skeleton />;
  const r = state.resources,
    agent = state.agent,
    ready = state.experts.filter((e) => e.status === "ready").length;
  const active = state.workers.experts.active_expert;
  const issues = Object.values(state.workers).filter(
    (w) => w.error && w.requested,
  );
  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200/60">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 px-5 py-4 sm:px-6">
          <div>
            <h2 className="text-base font-bold">실시간 운영</h2>
            <div className="mt-1 flex items-center gap-3 text-xs text-slate-400">
              <span>Champion MoE</span>
              <span>가상체결 {state.controls.paper ? "허용" : "정지"}</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <ControlButton name="feed" label="시세" compact />
            <ControlButton name="engine" label="MoE" compact />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-0 lg:grid-cols-4">
          {steps.map(({ role, label, icon: Icon, color }, i) => {
            const worker = state.workers[role],
              status = workerState(worker);
            return (
              <div
                key={role}
                className="relative flex gap-3 border-b border-slate-100 px-5 py-5 last:border-b-0 sm:border-b-0 sm:px-6"
              >
                <Icon size={22} className={`${color} mt-1 shrink-0`} />
                <div className="min-w-0">
                  <div className="text-sm font-semibold">{label}</div>
                  <div className="mt-2">
                    <Status tone={status.tone}>{status.label}</Status>
                  </div>
                  <p className="mt-2 truncate text-xs text-slate-400">
                    {role === "feed"
                      ? `${(state.feed.fresh_symbols_5m as string[] | undefined)?.length ?? 0}개 최신 종목`
                      : role === "experts"
                        ? active
                          ? (state.experts.find((e) => e.id === active)?.name ??
                            active)
                          : `${ready}개 출력 사용 가능`
                        : role === "agent"
                          ? agent.last_as_of
                            ? date(agent.last_as_of)
                            : "첫 시세 대기"
                          : state.learner.version != null
                            ? `정책 v${state.learner.version}`
                            : "첫 정책 대기"}
                  </p>
                </div>
                {i < 3 && (
                  <ArrowRight
                    size={15}
                    className="absolute right-0 top-8 hidden text-slate-200 sm:block"
                  />
                )}
              </div>
            );
          })}
        </div>
        {issues.length > 0 && (
          <div className="border-t border-rose-100 bg-rose-50 px-6 py-3 text-sm text-rose-700">
            {issues.map((w) => w.error).join(" · ")}
          </div>
        )}
      </section>
      {state.account&&<section className="grid gap-4 sm:grid-cols-2">
        {(['KRW','USD'] as const).map(currency=>{const book=state.account!.books[currency];return <a key={currency} href="#portfolio" onClick={()=>sessionStorage.setItem('portfolio_currency',currency)} className="rounded-xl bg-white px-5 py-4 transition hover:bg-blue-50/50">
          <h2 className="text-xs font-semibold text-slate-500">{accountNames[currency]}</h2>
          <div className="mt-2 flex flex-wrap items-baseline justify-between gap-3"><b className="text-xl tabular-nums">{money(book.equity,currency)}</b><span className={`text-sm ${book.pnl>=0?'text-rose-500':'text-blue-500'}`}>{money(book.pnl,currency)}</span></div>
          <p className="mt-2 text-xs text-slate-400">{book.positions.length}종목 · 이 계좌 누적 체결 {number(book.trade_count,0)}회 · 다른 통화와 합산 없음</p>
        </a>})}
      </section>}
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section className="rounded-2xl bg-[#edf3ff] p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-bold text-blue-900">
              <Cpu size={17} />
              장비 상태
            </h2>
            <a
              href="#system"
              className="text-xs font-medium text-blue-500 hover:text-blue-700"
            >
              프로세스 보기 →
            </a>
          </div>
          <div className="mt-5 grid gap-6 sm:grid-cols-2">
            <div>
              <div className="mb-1 text-xs text-slate-500">
                사용 중인 메모리
              </div>
              <div className="mb-3 text-xl font-bold tabular-nums">
                {bytes(r.ram_used_bytes)}
                <span className="ml-2 text-xs font-normal text-slate-400">
                  / {bytes(r.ram_total_bytes)}
                </span>
              </div>
              <Meter
                value={(r.ram_used_bytes / r.ram_total_bytes) * 100}
                color="bg-blue-500"
              />
              <p className="mt-2 text-xs text-slate-500">
                사용 가능 {bytes(r.ram_available_bytes)}
              </p>
            </div>
            <div>
              <div className="mb-1 truncate text-xs text-slate-500">
                {r.gpu.name ?? "GPU 측정 대기"}
              </div>
              <div className="mb-3 text-xl font-bold tabular-nums">
                {bytes(r.gpu.used_bytes)}
                <span className="ml-2 text-xs font-normal text-slate-400">
                  / {bytes(r.gpu.total_bytes)}
                </span>
              </div>
              <Meter
                value={
                  ((r.gpu.used_bytes ?? 0) / (r.gpu.total_bytes ?? 1)) * 100
                }
                color="bg-violet-500"
              />
              <p className="mt-2 text-xs text-slate-500">
                GPU 사용률 {number(r.gpu.utilization_percent)}%
              </p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-t border-blue-200/40 pt-4 text-xs text-slate-500">
            <span>
              CPU{" "}
              <b className="ml-1 text-slate-700">{number(r.cpu_percent)}%</b>
            </span>
            <span>
              디스크 여유{" "}
              <b className="ml-1 text-slate-700">{bytes(r.disk_free_bytes)}</b>
            </span>
            <span>
              판단 시간{" "}
              <b className="ml-1 text-slate-700">
                {agent.decision_seconds == null
                  ? "첫 판단 대기"
                  : `${number(agent.decision_seconds, 3)}s`}
              </b>
            </span>
          </div>
        </section>
        <section className="px-1 py-2">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-bold">
              <Database size={17} className="text-violet-500" />
              경험 · 가중치
            </h2>
            <a
              href="#learning"
              className="text-xs font-medium text-slate-400 hover:text-blue-600"
            >
              학습 보기 →
            </a>
          </div>
          <div className="flex items-end gap-3">
            <span className="text-4xl font-bold tabular-nums tracking-tight">
              {number(
                (agent.source_updates ?? 0) +
                  (state.learner.optimizer_steps ?? 0),
                0,
              )}
            </span>
            <span className="pb-1.5 text-sm text-slate-400">
              누적 가중치 업데이트
            </span>
          </div>
          <div className="mt-5 space-y-3">
            {[
              {
                label: "결과 확정 대기",
                value: state.replay.pending,
                color: "bg-amber-400",
              },
              {
                label: "학습 대기",
                value: state.replay.ready,
                color: "bg-violet-500",
              },
              {
                label: "학습 완료",
                value: state.replay.completed,
                color: "bg-emerald-500",
              },
            ].map((item) => (
              <div className="flex items-center gap-3" key={item.label}>
                <span className={`size-2 rounded-sm ${item.color}`} />
                <span className="flex-1 text-sm text-slate-500">
                  {item.label}
                </span>
                <b className="tabular-nums">{number(item.value, 0)}</b>
              </div>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-2 text-xs text-slate-400">
            <CheckCircle2 size={14} />
            원본 Expert 가중치는 고정 · 경험 저장 {bytes(state.replay.bytes)}
          </div>
        </section>
      </div>
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold">최근 판단</h2>
          <a
            href="#portfolio"
            className="text-xs text-slate-400 hover:text-blue-600"
          >
            계좌 · 체결 →
          </a>
        </div>
        {state.decisions.length ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[...state.decisions]
              .sort((a,b)=>b.as_of.localeCompare(a.as_of)
                ||Math.abs(b.target_weight-b.current_weight)-Math.abs(a.target_weight-a.current_weight))
              .slice(0, 8).map((d) => (
              <a
                href="#portfolio"
                key={d.symbol}
                className="flex items-center justify-between rounded-xl bg-white px-4 py-3 transition hover:shadow-md"
              >
                <div>
                  <b className="text-sm">{d.symbol}</b>
                  <div className="mt-1 text-xs text-slate-400">
                    {date(d.as_of)}
                  </div>
                </div>
                <div className="text-right">
                  <span
                    className={`text-xs font-semibold ${d.action === "BUY" ? "text-rose-500" : d.action === "SELL" ? "text-blue-500" : "text-slate-400"}`}
                  >
                    {d.action === "BUY"
                      ? "매수"
                      : d.action === "SELL"
                        ? "매도"
                        : "보유"}
                  </span>
                  <div className="mt-1 text-sm font-semibold tabular-nums">
                    {number(d.current_weight * 100)} →{" "}
                    {number(d.target_weight * 100)}%
                  </div>
                </div>
              </a>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200">
            <Empty
              title="아직 판단이 없습니다."
              detail="시세와 실제 Expert 출력이 준비되면 MoE의 판단이 표시됩니다."
            />
          </div>
        )}
      </section>
    </div>
  );
}
