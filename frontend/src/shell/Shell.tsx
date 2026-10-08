import { useCallback, useState, type ReactNode } from "react";
import {
  Activity,
  Bell,
  Boxes,
  ChartCandlestick,
  CircuitBoard,
  GraduationCap,
  Link2,
  LockKeyhole,
  Wallet,
} from "lucide-react";
import { useOperations } from "../data/Operations";
import { request } from "../data/api";
import { Drawer, Empty, ErrorMessage, Status } from "../ui/Primitives";
import { date } from "../ui/format";

export const navigation = [
  { hash: "control", name: "운영", icon: Activity },
  { hash: "moe", name: "MoE", icon: Boxes },
  { hash: "markets", name: "시장", icon: ChartCandlestick },
  { hash: "portfolio", name: "계좌", icon: Wallet },
  { hash: "learning", name: "학습", icon: GraduationCap },
  { hash: "connection", name: "연결", icon: Link2 },
  { hash: "system", name: "진단", icon: CircuitBoard },
];

export function Shell({
  active,
  children,
}: {
  active: string;
  children: ReactNode;
}) {
  const { state, error, refresh } = useOperations();
  const [alerts, setAlerts] = useState(false),
    [readThrough, setReadThrough] = useState(0);
  const unread =
    state?.events.filter((e) => !e.read && e.id > readThrough).length ?? 0;
  const close = useCallback(() => setAlerts(false), []);
  const open = async () => {
    setAlerts(true);
    const last = Math.max(0, ...(state?.events.map((e) => e.id) ?? []));
    setReadThrough(last);
    try {
      await request("events/read", {through:last});
      await refresh();
    } catch {
      setReadThrough(0);
    }
  };
  return (
    <div className="min-h-dvh bg-[#f4f6fa] text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-[1500px] flex-wrap items-center justify-between gap-x-5 gap-y-3 px-4 py-3 sm:px-7 lg:flex-nowrap">
          <a
            href="#control"
            className="flex shrink-0 items-center gap-2.5 font-bold tracking-tight"
          >
            <span className="grid size-8 place-items-center rounded-xl bg-blue-600 text-white">
              <Activity size={19} />
            </span>
            <span>
              FinRL-X
              <span className="ml-2 text-xs font-medium text-slate-400">
                MoE
              </span>
            </span>
          </a>
          <nav
            aria-label="주요 화면"
            className="order-3 grid w-full grid-cols-4 gap-1 sm:flex sm:w-auto sm:flex-1 sm:justify-center lg:order-2"
          >
            {navigation.map(({ hash, name, icon: Icon }) => (
              <a
                key={hash}
                href={`#${hash}`}
                aria-current={active === hash ? "page" : undefined}
                className={`flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-[13px] font-semibold transition hover:bg-slate-50 ${active === hash ? "bg-blue-50 text-blue-700" : "text-slate-500"}`}
              >
                <Icon size={16} />
                {name}
              </a>
            ))}
          </nav>
          <div className="order-2 flex items-center gap-4 lg:order-3">
            <span className="hidden items-center gap-1.5 text-xs text-slate-400 sm:flex">
              <LockKeyhole size={13} />
              실주문 꺼짐
            </span>
            <Status tone={error ? "bad" : state ? "good" : "idle"}>
              {error ? "연결 끊김" : state ? "서버 연결" : "연결 중"}
            </Status>
            <button
              aria-label={`알림 ${unread}개`}
              onClick={() => void open()}
              className="relative grid size-9 place-items-center rounded-xl text-slate-500 transition hover:bg-slate-100"
            >
              <Bell size={18} />
              {unread > 0 && (
                <span className="absolute right-1 top-1 size-2 rounded-full bg-rose-500 ring-2 ring-white" />
              )}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-7 sm:py-8">
        <div className="mb-5 flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight">
            {navigation.find((n) => n.hash === active)?.name ?? "운영"}
          </h1>
          {state && (
            <time className="text-xs tabular-nums text-slate-400">
              {date(state.time)} 기준
            </time>
          )}
        </div>
        {error && (
          <div className="mb-5">
            <ErrorMessage message={error} />
          </div>
        )}
        {children}
      </main>
      <Drawer title="알림" open={alerts} onClose={close}>
        <p className="mb-4 text-xs leading-5 text-slate-400">
          실행 오류, 학습 완료, 정책 복원 기록
        </p>
        {state?.events.length ? (
          <ol className="space-y-3">
            {state.events.map((event) => (
              <li className="rounded-xl bg-slate-50 p-4" key={event.id}>
                <div className="flex items-center justify-between gap-3">
                  <Status
                    tone={
                      event.kind === "error"
                        ? "bad"
                        : event.kind === "warning"
                          ? "warn"
                          : "good"
                    }
                  >
                    {event.kind === "error"
                      ? "오류"
                      : event.kind === "warning"
                        ? "주의"
                        : "학습"}
                  </Status>
                  <time className="text-xs text-slate-400">
                    {date(event.time)}
                  </time>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {event.detail}
                </p>
              </li>
            ))}
          </ol>
        ) : (
          <Empty title="새 알림이 없습니다." />
        )}
      </Drawer>
    </div>
  );
}
