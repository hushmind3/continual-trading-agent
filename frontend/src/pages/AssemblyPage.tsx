import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { ArrowDown, ArrowRight, Check, Cpu, FolderOpen, LoaderCircle, Play, Square, Wrench } from "lucide-react";
import type { AssemblyBuild, Expert } from "../api/types";
import { Action, Empty, Progress, QueryState } from "../components/controls";
import { useWorkspace } from "../state/Workspace";

function ExpertRow({ expert, selected, onToggle }: { expert: Expert; selected: boolean; onToggle: () => void }) {
  return <button type="button" onClick={onToggle} aria-pressed={selected} className={`group flex w-full items-center gap-3 border-b border-white/8 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-white/6 focus-visible:bg-white/8 focus-visible:outline-none ${selected ? "bg-sky-400/10" : ""}`}>
    <span className={`flex size-5 shrink-0 items-center justify-center rounded-md border ${selected ? "border-sky-300 bg-sky-300 text-slate-950" : "border-white/20 text-transparent"}`}><Check size={13} strokeWidth={3} /></span>
    <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium text-slate-100">{expert.name}</span><span className="mt-0.5 block truncate text-xs text-slate-500">{expert.description || (expert.universe?.length ? expert.universe.join(", ") : "공통 시장 입력")}</span></span>
    <span className="shrink-0 text-xs text-slate-500">{expert.universe?.length ? expert.universe.length + " 종목" : "공통"}</span>
  </button>;
}

function ExpertColumn({ title, caption, experts, selected, onToggle }: { title: string; caption: string; experts: Expert[]; selected: Set<string>; onToggle: (id: string) => void }) {
  return <section className="min-w-0 overflow-hidden rounded-2xl border border-white/10 bg-slate-900/70">
    <header className="flex items-end justify-between border-b border-white/10 px-4 py-3"><div><h2 className="text-sm font-semibold text-slate-100">{title}</h2><p className="mt-1 text-xs text-slate-500">{caption}</p></div><span className="text-sm tabular-nums text-sky-300">{selected.size}/{experts.length}</span></header>
    <div className="max-h-[34rem] overflow-y-auto">{experts.length ? experts.map((expert) => <ExpertRow key={expert.id} expert={expert} selected={selected.has(expert.id)} onToggle={() => onToggle(expert.id)} />) : <Empty>등록된 전문가가 없습니다.</Empty>}</div>
  </section>;
}

function FlowNode({ title, detail, tone = "neutral" }: { title: string; detail?: string; tone?: "neutral" | "sky" | "violet" | "emerald" }) {
  const toneClass = { neutral: "border-white/10 bg-white/5 text-slate-200", sky: "border-sky-300/25 bg-sky-400/10 text-sky-100", violet: "border-violet-300/25 bg-violet-400/10 text-violet-100", emerald: "border-emerald-300/25 bg-emerald-400/10 text-emerald-100" }[tone];
  return <div className={`rounded-lg border px-3 py-2 text-center ${toneClass}`}><div className="text-xs font-semibold">{title}</div>{detail && <div className="mt-1 text-[11px] opacity-70">{detail}</div>}</div>;
}

function Pipeline({ marketCount, actionCount }: { marketCount: number; actionCount: number }) {
  return <section className="rounded-2xl border border-sky-300/20 bg-sky-400/7 p-5">
    <div className="flex items-center gap-2 text-xs font-medium text-sky-300"><Cpu size={15} /> 생성 구조</div>
    <div className="mt-4 space-y-3 text-sm">
      <div className="grid gap-3 md:grid-cols-2">
        <div className="space-y-2"><FlowNode title={`시장 분석 Expert ${marketCount}개`} detail="병렬 입력" tone="sky" /><ArrowDown className="mx-auto text-slate-600" size={14} /><FlowNode title="Market Router" /><ArrowDown className="mx-auto text-slate-600" size={14} /><FlowNode title="Market Fusion" /><ArrowDown className="mx-auto text-slate-600" size={14} /><FlowNode title="Market Latent" detail="시장 표현" tone="sky" /></div>
        <div className="space-y-2"><FlowNode title={`매매 판단 Expert ${actionCount}개`} detail="원본 Action / Q 보존" tone="violet" /><ArrowDown className="mx-auto text-slate-600" size={14} /><FlowNode title="Policy Adapter · Router" /><ArrowDown className="mx-auto text-slate-600" size={14} /><FlowNode title="Policy Attention" detail="시장 Query 결합" tone="violet" /></div>
      </div>
      <div className="flex items-center justify-center gap-2 text-[11px] text-amber-200"><ArrowRight size={14} /><span>Action Prior · 원본 BUY / HOLD / SELL + Q</span><ArrowRight size={14} /></div>
      <div className="flex justify-center"><FlowNode title="Final Controller" detail="Market + Policy + 계좌상태 + Action Prior" tone="emerald" /></div>
      <ArrowDown className="mx-auto text-slate-600" size={14} />
      <FlowNode title="행동 + 목표 비중" detail="SELL · HOLD · BUY" tone="emerald" />
    </div>
  </section>;
}

function BuildStatus({ build }: { build?: AssemblyBuild }) {
  if (!build || build.status === "idle") return <div className="rounded-xl border border-dashed border-white/12 px-4 py-5 text-sm text-slate-500">전문가를 선택하고 TradingMoE 생성을 시작하면 진행 상태가 여기에 표시됩니다.</div>;
  const active = build.status === "queued" || build.status === "running";
  return <div className={`rounded-xl border px-4 py-4 ${build.status === "error" ? "border-rose-300/30 bg-rose-400/8" : build.status === "ready" ? "border-emerald-300/30 bg-emerald-400/8" : "border-sky-300/20 bg-sky-400/6"}`}>
    <div className="flex items-center gap-2">{active ? <LoaderCircle size={16} className="animate-spin text-sky-300" /> : <span className={`size-2 rounded-full ${build.status === "ready" ? "bg-emerald-300" : build.status === "error" ? "bg-rose-300" : "bg-slate-500"}`} />}<strong className="text-sm text-slate-100">{build.phase}</strong>{build.progress !== undefined && build.progress > 0 && <span className="ml-auto text-xs tabular-nums text-slate-400">{build.progress}%</span>}</div>
    <p className="mt-2 text-xs leading-5 text-slate-400">{build.message}</p>{active && <Progress value={build.progress} total={100} label="TradingMoE 생성 진행률" />}{build.path && <p className="mt-3 break-all font-mono text-[11px] text-slate-500">{build.path}</p>}{build.bytes ? <p className="mt-1 text-xs text-slate-500">생성 파일 {(build.bytes / 1024 / 1024 / 1024).toFixed(2)} GB</p> : null}
  </div>;
}

export function AssemblyPage() {
  const { assembly, registry, command, pending } = useWorkspace();
  const data = assembly.data;
  const [marketSelection, setMarketSelection] = useState<Set<string>>(new Set());
  const [actionSelection, setActionSelection] = useState<Set<string>>(new Set());
  const experts = useMemo(() => { const fromAssembly = new Map((data?.experts ?? []).map((expert) => [expert.id, expert])); return (registry.data?.experts ?? data?.experts ?? []).map((expert) => ({ ...expert, ...(fromAssembly.get(expert.id) ?? {}) })); }, [data?.experts, registry.data?.experts]);
  const marketExperts = useMemo(() => experts.filter((expert) => expert.role === "market"), [experts]);
  const actionExperts = useMemo(() => experts.filter((expert) => expert.role === "policy" || expert.role === "action"), [experts]);
  useEffect(() => { setMarketSelection((current) => current.size ? current : new Set(marketExperts.filter((expert) => expert.eligible !== false).map((expert) => expert.id))); setActionSelection((current) => current.size ? current : new Set(actionExperts.filter((expert) => expert.eligible !== false).map((expert) => expert.id))); }, [marketExperts, actionExperts]);
  const build = data?.build;
  const building = build?.status === "queued" || build?.status === "running";
  const ready = build?.status === "ready";
  const selectedCount = marketSelection.size + actionSelection.size;
  const toggle = (set: Dispatch<SetStateAction<Set<string>>>, id: string) => set((current) => { const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next; });
  const create = () => void command("/api/assembly/build", { market_experts: [...marketSelection], action_experts: [...actionSelection] }, "TradingMoE 생성", "assembly-build");
  const cancel = () => void command("/api/assembly/build/cancel", {}, "TradingMoE 생성 취소", "assembly-build-cancel");
  return <>
    <QueryState {...assembly} /><QueryState {...registry} />
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><div className="flex items-center gap-2 text-xs font-medium text-sky-300"><Wrench size={14} /> 전문가 구성</div><h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-50">MoE 생성</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">시장 분석 전문가와 매매 판단 전문가를 선택해 Controller 위에 연결하고, 독립 TradingMoE.pt를 생성합니다.</p></div><div className="flex items-center gap-2">{building ? <Action onClick={cancel}><Square size={15} />생성 취소</Action> : <Action primary disabled={selectedCount === 0 || !!pending["assembly-build"]} onClick={create}><Play size={15} />TradingMoE 생성</Action>}</div></div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_360px]"><ExpertColumn title="시장 분석" caption="1층 · 병렬 분석" experts={marketExperts} selected={marketSelection} onToggle={(id) => toggle(setMarketSelection, id)} /><ExpertColumn title="매매 판단" caption="2층 · 병렬 정책" experts={actionExperts} selected={actionSelection} onToggle={(id) => toggle(setActionSelection, id)} /><aside className="space-y-5 xl:sticky xl:top-24 xl:self-start"><Pipeline marketCount={marketSelection.size} actionCount={actionSelection.size} /><section className="rounded-2xl border border-white/10 bg-slate-900/70 p-5"><div className="flex items-center justify-between"><h2 className="text-sm font-semibold text-slate-100">생성 결과</h2><span className="text-xs text-slate-500">{selectedCount}개 선택</span></div><div className="mt-4"><BuildStatus build={build} /></div>{ready && <Action primary className="mt-4 w-full" disabled={!!pending["assembly-register"]} onClick={() => void command("/api/assembly/register", {}, "Candidate 등록", "assembly-register")}>Candidate로 등록</Action>}{build?.status === "registered" && <div className="mt-4 flex items-center gap-2 text-xs text-emerald-200"><FolderOpen size={14} /> Candidate로 등록되었습니다.</div>}</section></aside></div>
  </>;
}
