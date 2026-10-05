import { X } from "lucide-react";
import type { WorkspaceState } from "../state/Workspace";
import { date } from "../format";
type Props = Pick<WorkspaceState, "notice" | "setNotice" | "events">;
export function NotificationPanel({ notice, setNotice, events }: Props) {
  return (
    <>
      {notice && (
        <section className="fixed right-5 top-20 z-50 w-[min(320px,calc(100vw-40px))] rounded-2xl border border-white/10 bg-[#243044] p-5 shadow-xl">
          <div className="mb-4 flex justify-between text-sm font-semibold">
            중요 알림
            <button aria-label="알림 닫기" onClick={() => setNotice(false)}>
              <X size={16} />
            </button>
          </div>
          {events.length ? (
            <div className="max-h-80 overflow-auto">
              {events.map((event) => (
                <div key={event.id} className="border-t border-white/10 py-3">
                  <p
                    className={`text-xs leading-5 ${event.error ? "text-rose-300" : "text-slate-200"}`}
                  >
                    {event.text}
                  </p>
                  <span className="text-[10px] text-slate-500">
                    {date(event.time)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-6 text-center text-xs text-slate-400">
              새 알림이 없습니다.
            </p>
          )}
        </section>
      )}
    </>
  );
}
