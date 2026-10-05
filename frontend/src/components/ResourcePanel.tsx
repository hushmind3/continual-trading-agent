import { ArrowRight, Cpu, Zap } from "lucide-react";
import { useWorkspace } from "../state/Workspace";
import { bytes, date, number } from "../format";
export function ResourcePanel({ onDetails }: { onDetails: () => void }) {
  const { status, models, events, connected } = useWorkspace();
  const gpu = connected ? status.data?.physical_gpu : undefined;
  const utilization = gpu?.utilization_percent;
  const weights = models.map(
    (model) => model.data.ram_weight_bytes ?? model.data.worker_ram_bytes,
  );
  const ram =
    models.every((model) => model.available) &&
    weights.every((value) => value !== undefined)
      ? weights.reduce<number>((total, value) => total + (value ?? 0), 0)
      : undefined;
  return (
    <aside className="grid content-start gap-6 sm:grid-cols-2 xl:grid-cols-1">
      <section className="rounded-2xl bg-[#dcebf4] p-6 text-slate-900">
        <div className="mb-6 flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold">
            <Cpu size={18} />
            계산 자원
          </span>
          <span className="text-[10px] text-slate-500">전체 GPU</span>
        </div>
        <div className="mb-7">
          <div className="mb-2 flex items-baseline gap-1">
            <strong className="text-5xl font-semibold tracking-tight">
              {number(utilization)}
            </strong>
            <span className="text-xl text-slate-500">%</span>
          </div>
          <p className="text-xs text-slate-500">GPU 사용률</p>
        </div>
        <div
          className="flex h-9 items-end gap-1"
          aria-label={`GPU 사용률 ${number(utilization)}퍼센트`}
        >
          {Array.from({ length: 20 }, (_, i) => (
            <span
              key={i}
              className={`h-full flex-1 rounded-[3px] ${i < Math.round((utilization ?? 0) / 5) ? "bg-sky-500" : "bg-slate-900/8"}`}
            />
          ))}
        </div>
        <div className="mt-5 space-y-3 text-xs">
          <div className="flex justify-between">
            <span className="text-slate-500">GPU 메모리</span>
            <strong>
              {gpu?.memory_used_mb !== undefined &&
              gpu.memory_total_mb !== undefined
                ? `${number(gpu.memory_used_mb / 1024, 2)} / ${number(gpu.memory_total_mb / 1024, 2)} GB`
                : "미수신"}
            </strong>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">모델 RAM</span>
            <strong>{bytes(ram)}</strong>
          </div>
        </div>
        <button
          onClick={onDetails}
          className="mt-6 flex items-center gap-2 text-xs font-semibold text-sky-700"
        >
          자원 상세
          <ArrowRight size={13} />
        </button>
      </section>
      <section className="px-1">
        <h2 className="mb-5 flex items-center gap-2 text-sm font-medium">
          <Zap size={15} className="text-amber-300" />
          상태 변화
        </h2>
        <div className="border-l border-white/10 pl-4">
          {events.length ? (
            events.slice(0, 5).map((event) => (
              <div key={event.id} className="mb-4">
                <p
                  className={`text-xs leading-5 ${event.error ? "text-rose-300" : "text-slate-300"}`}
                >
                  {event.text}
                </p>
                <span className="text-[10px] text-slate-500">
                  {date(event.time)}
                </span>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500">
              새로운 상태 변화가 없습니다.
            </p>
          )}
        </div>
      </section>
    </aside>
  );
}
