import { Legend } from "./components/controls";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { NotificationPanel } from "./components/NotificationPanel";
import { DetailDrawer } from "./components/DetailDrawer";
import { PageRouter } from "./pages/PageRouter";
import { destinations } from "./config";
import { useWorkspace } from "./state/Workspace";

export default function App() {
  const state = useWorkspace();
  const { page } = state;
  return (
    <div className="min-h-screen bg-[#101725]">
      <Header {...state} />
      <div className="mx-auto flex max-w-[1680px]">
        <Sidebar {...state} />
        <main className="min-w-0 flex-1 px-5 py-7 sm:px-7 lg:px-10 lg:py-9">
          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <span className="h-10 w-1 rounded-full bg-sky-400" />
              <div>
                <p className="mb-1 text-xs text-slate-500">
                  {page === 0 ? "전체 실행 상황" : "현재 상태"}
                </p>
                <h1 className="text-[27px] font-semibold tracking-tight">
                  {destinations[page].name}
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl bg-white/5 px-4 py-2.5">
              <Legend on={state.connected}>
                {state.connected ? "서버 연결됨" : "서버 연결 대기"}
              </Legend>
              <span className="h-3 w-px bg-white/15" />
              <span className="text-[11px] text-slate-500">
                {!state.connected
                  ? "실제 주문 상태 미수신"
                  : state.status.data?.real_orders_enabled
                    ? "실제 주문 허용"
                    : "실제 주문 차단"}
              </span>
            </div>
          </div>
          <PageRouter />
          <NotificationPanel {...state} />
        </main>
      </div>
      <DetailDrawer {...state} />
    </div>
  );
}
