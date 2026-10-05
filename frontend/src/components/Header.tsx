import { Bell, Command, Menu, Network, X } from "lucide-react";
import type { WorkspaceState } from "../state/Workspace";
type Props = Pick<
  WorkspaceState,
  "menu" | "setMenu" | "notice" | "setNotice" | "unread" | "setSelected"
>;
export function Header({
  menu,
  setMenu,
  notice,
  setNotice,
  setSelected,
  unread,
}: Props) {
  return (
    <header className="sticky top-0 z-40 flex h-[68px] items-center justify-between border-b border-white/7 bg-[#101725]/95 px-5 backdrop-blur-xl lg:px-8">
      <div className="flex items-center gap-3">
        <button
          aria-label="메뉴 열기"
          onClick={() => setMenu(!menu)}
          className="rounded-lg p-2 text-slate-300 hover:bg-white/10 lg:hidden"
        >
          {menu ? <X size={20} /> : <Menu size={20} />}
        </button>
        <span className="flex size-9 items-center justify-center rounded-xl bg-sky-400 text-slate-950">
          <Network size={21} />
        </span>
        <strong className="text-lg tracking-tight">TradingMoE</strong>
        <span className="ml-3 hidden border-l border-white/15 pl-4 text-xs text-slate-500 sm:block">
          운영 콘솔
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="rounded-md bg-amber-300/10 px-2.5 py-1 text-[10px] font-semibold text-amber-200">
          가상매매
        </span>
        <button
          onClick={() => setNotice(!notice)}
          aria-label="알림"
          aria-expanded={notice}
          className="relative rounded-xl p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"
        >
          <Bell size={19} />
          {unread && (
            <span
              data-testid="unread-indicator"
              className="absolute right-1 top-1 size-1.5 rounded-full bg-amber-300"
            />
          )}
        </button>
        <button
          onClick={() => {
            setSelected("빠른 실행");
          }}
          aria-label="빠른 실행"
          className="hidden rounded-lg bg-white/5 p-2 text-slate-400 hover:text-sky-300 sm:block"
        >
          <Command size={17} />
        </button>
      </div>
    </header>
  );
}
