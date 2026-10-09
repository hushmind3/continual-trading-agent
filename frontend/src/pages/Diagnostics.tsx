import { Activity, CircuitBoard, FileText } from "lucide-react";
import { useOperations } from "../data/Operations";
import { Empty, Skeleton } from "../ui/Primitives";
import { bytes, date, number } from "../ui/format";
import { TrainingReadiness } from "../ui/TrainingReadiness";
import {ServiceProgress} from '../ui/ServiceProgress';

const roles: Record<string, string> = {
  feed: "시세 수집",
  experts: "Expert 실행",
  agent: "MoE · 가상계좌",
  learner: "SAC 학습",
};
export function Diagnostics() {
  const { state } = useOperations();
  if (!state) return <Skeleton />;
  return (
    <div className="space-y-6">
      <section className="overflow-auto rounded-2xl bg-white shadow-sm ring-1 ring-slate-200/50">
        <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-4 text-sm font-bold">
          <CircuitBoard size={17} className="text-blue-500" />
          실행 단계 · 통합 MoE는 같은 PID를 공유합니다
        </div>
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-400">
            <tr>
              {["대상", "상태", "PID", "RAM", "CPU · 코어 합산", "I/O 누적"].map(
                (label) => (
                  <th
                    key={label}
                    className="whitespace-nowrap px-5 py-4 font-medium"
                  >
                    {label}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {Object.entries(state.workers).map(([role, worker]) => {
              const resource = state.resources.processes.find(
                  (p) => p.role === role || p.roles?.includes(role),
                );
              return (
                <tr key={role} className="border-t border-slate-50">
                  <td className="whitespace-nowrap px-5 py-4 font-semibold">
                    {roles[role] ?? role}
                  </td>
                  <td className="px-5 py-4">
                    {role==='learner'&&<TrainingReadiness compact/>}<ServiceProgress role={role} showState={role!=='learner'}/>
                  </td>
                  <td className="px-5 py-4 font-mono text-xs text-slate-400">
                    {worker.pid ?? "정지"}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 tabular-nums">
                    {resource?.role==='moe'&&role!=='experts'?'위 통합 MoE와 공유':bytes(resource?.rss_bytes)}
                  </td>
                  <td className="px-5 py-4 tabular-nums">
                    {resource?.role==='moe'&&role!=='experts'?'공유':resource ? number(resource.cpu_percent) + "%" : "정지"}
                  </td>
                  <td className="whitespace-nowrap px-5 py-4 text-xs text-slate-400">
                    {resource?.role==='moe'&&role!=='experts'?'공유':resource
                      ? `${bytes(resource.read_bytes)} 읽기 / ${bytes(resource.write_bytes)} 쓰기`
                      : "정지"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
      <div className="grid gap-6 lg:grid-cols-2">
            <section className="min-w-0">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-bold">
            <Activity size={16} />
            운영 이벤트
          </h2>
          {state.events.length ? (
            <ol className="space-y-3">
              {state.events.slice(0, 20).map((event) => (
                <li
                  key={event.id}
                  className="flex gap-3 rounded-xl bg-white px-4 py-3"
                >
                  <span
                    className={`mt-1.5 size-2 shrink-0 rounded-full ${event.kind === "error" ? "bg-rose-500" : event.kind === "warning" ? "bg-amber-400" : "bg-emerald-500"}`}
                  />
                  <div>
                          <p className="break-all text-sm leading-6 text-slate-600">
                      {event.detail}
                    </p>
                    <time className="mt-1 block text-xs text-slate-400">
                      {date(event.time)}
                    </time>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <Empty title="기록된 이벤트가 없습니다." />
          )}
        </section>
        <section className="space-y-4">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-bold">
            <FileText size={16} />
            진단 데이터
          </h2>
          {["workers", "feed", "replay", "resources", "settings"].map((key) => (
            <details key={key} className="rounded-xl bg-white px-4 py-3">
              <summary className="cursor-pointer text-sm font-medium text-slate-600">
                {
                  (
                    {
                      workers: "프로세스 상태",
                      feed: "시세 수신",
                      replay: "경험 저장소",
                      resources: "자원 측정",
                      settings: "적용 설정",
                    } as Record<string, string>
                  )[key]
                }
              </summary>
              <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-[11px] leading-5 text-slate-300">
                {JSON.stringify(state[key as keyof typeof state], null, 2)}
              </pre>
            </details>
          ))}
        </section>
      </div>
    </div>
  );
}
