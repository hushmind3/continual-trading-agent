import { ShieldCheck } from "lucide-react";
import { destinations } from "../config";
import type { WorkspaceState } from "../state/Workspace";
type Props = Pick<WorkspaceState, "menu" | "setMenu" | "page" | "setPage">;
export function Sidebar({ menu, setMenu, page, setPage }: Props) {
  return (
    <>
      {menu && (
        <button
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          aria-label="메뉴 닫기"
          onClick={() => setMenu(false)}
        />
      )}
      <nav
        aria-label="주요 메뉴"
        className={`fixed bottom-0 left-0 top-[68px] z-50 w-[220px] shrink-0 border-r border-white/7 bg-[#101725] p-5 transition-transform duration-300 lg:sticky lg:top-[68px] lg:z-20 lg:h-[calc(100dvh-68px)] lg:translate-x-0 ${menu ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="mb-6 px-3 pt-2 text-[10px] tracking-widest text-slate-600">
          WORKSPACE
        </div>
        <div className="space-y-1.5">
          {destinations.map((m, i) => (
            <button
              key={m.name}
              onClick={() => {
                setPage(i);
                setMenu(false);
              }}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm transition-colors ${page === i ? "bg-sky-400/12 font-semibold text-sky-300" : "text-slate-400 hover:bg-white/5 hover:text-blue-300"}`}
            >
              <m.icon size={18} />
              {m.name}
              {page === i && (
                <span className="ml-auto size-1 rounded-full bg-sky-300" />
              )}
            </button>
          ))}
        </div>
        <div className="mt-9 rounded-xl bg-white/3 p-3.5">
          <div className="mb-2 flex items-center gap-2 text-xs text-slate-300">
            <ShieldCheck size={14} className="text-teal-300" />
            가상매매
          </div>
          <p className="text-[10px] leading-5 text-slate-500">
            모델별 계좌로 가상매매합니다.
            <br />
            실행 상태는 서버에서 갱신됩니다.
          </p>
        </div>
      </nav>
    </>
  );
}
