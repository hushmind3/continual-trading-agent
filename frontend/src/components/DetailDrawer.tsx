import { Pause, Play, X } from "lucide-react";
import { Action } from "./controls";
import type { WorkspaceState } from "../state/Workspace";
import { bytes, date, number, seconds } from "../format";
type Props = Pick<
  WorkspaceState,
  "selected" | "setSelected" | "models" | "toggleModel" | "setPage"
>;
export function DetailDrawer({
  selected,
  setSelected,
  models,
  toggleModel,
  setPage,
}: Props) {
  const model = models.find((entry) => entry.name === selected);
  return (
    <>
      {selected && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          onClick={() => setSelected(null)}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label={selected}
            onClick={(e) => e.stopPropagation()}
            className="absolute bottom-0 right-0 w-full rounded-t-3xl border border-white/10 bg-[#1d293c] p-7 shadow-2xl sm:bottom-0 sm:top-0 sm:w-[360px] sm:rounded-none"
          >
            <header className="mb-7 flex items-center justify-between">
              <h2 className="text-xl font-semibold">{selected}</h2>
              <button
                aria-label="상세 닫기"
                onClick={() => setSelected(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-white/10"
              >
                <X size={20} />
              </button>
            </header>
            {model ? <>
              <p className={`mb-6 text-lg ${model.running?'text-emerald-300':'text-slate-400'}`}>{model.displayStatus}</p>
              <dl className="mb-7 space-y-4 text-sm">
                <div className="flex justify-between"><dt className="text-slate-400">모델 적재</dt><dd>{!model.available?'확인 불가':model.data.loaded?'적재됨':'미적재'}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-400">학습</dt><dd>{model.running&&model.data.learning_active?'진행 중':'대기'}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-400">가중치 업데이트</dt><dd>{number(model.data.optimizer_updates)}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-400">학습 대기 경험</dt><dd>{number(model.data.replay?.untrained??model.data.replay?.eligible)}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-400">최근 판단</dt><dd>{date(model.data.last_decision??model.data.decision?.as_of)}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-400">판단 소요 시간</dt><dd>{seconds(model.data.decision_seconds??model.data.decision?.seconds)}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-400">모델 RAM</dt><dd>{bytes(model.data.ram_weight_bytes??model.data.worker_ram_bytes)}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-400">모델 VRAM</dt><dd>{bytes(model.data.gpu_weight_bytes??(model.data.alive?model.data.compute?.allocated_bytes:0))}</dd></div>
              </dl>
              {model.data.error&&<p role="alert" className="mb-5 break-words text-sm text-rose-300">{model.data.error}</p>}
              <Action disabled={!model.available||model.busy||['loading','starting','saving','stopping'].includes(model.data.status??'')} primary={!model.enabled} onClick={() => toggleModel(model.name)}>
                {model.enabled ? <Pause size={16} /> : <Play size={16} />}
                {model.busy?'요청 중':model.enabled?'저장 후 정지':'시작'}
              </Action>
            </> : selected==='빠른 실행' ? <div className="space-y-3">
              {models.map(entry=><Action key={entry.role} disabled={!entry.available||entry.busy||['loading','starting','saving','stopping'].includes(entry.data.status??'')} onClick={()=>toggleModel(entry.name)} className="w-full justify-between"><span>{entry.name}</span><span>{entry.busy?'요청 중':entry.enabled?'저장 후 정지':'시작'}</span></Action>)}
              <Action onClick={()=>{setPage(1);setSelected(null);}} className="w-full">자동매매 화면 열기</Action>
            </div> : null}
          </section>
        </div>
      )}
    </>
  );
}
