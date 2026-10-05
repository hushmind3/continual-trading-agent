import { useEffect, useRef, useState } from "react";
import { ArrowLeft, BookOpen, Search, X } from "lucide-react";
import type { Expert, Recipe } from "../../api/types";
import { request } from "../../api/client";
import { Action, Empty } from "../../components/controls";
import {
  bytes,
  compactNumber,
  date,
  expertName,
  expertRole,
  expertUniverse,
  number,
  seconds,
  symbolName,
} from "../../format";

export function ExpertCatalog({
  experts,
  candidate,
  newExperts,
  selectedId,
  onSelect,
  onClose,
}: {
  experts: Expert[];
  candidate?: Recipe;
  newExperts: string[];
  selectedId: string;
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [search, setSearch] = useState("");
  const selected = experts.find((expert) => expert.id === selectedId);
  const filtered = experts.filter((expert) =>
    `${expertName(expert)} ${expert.name} ${expert.description ?? ""} ${expertRole(expert.role)}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      aria-labelledby="expert-reference-title"
      onClose={onClose}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right)
          onClose();
      }}
      className="fixed inset-y-0 left-auto right-0 m-0 h-dvh max-h-none w-full max-w-md overflow-y-auto border-l border-white/10 bg-[#172131] p-5 text-slate-200 shadow-2xl backdrop:bg-black/50"
    >
      <header className="mb-5 flex items-center justify-between gap-3">
        {selected ? (
          <button
            onClick={() => onSelect("")}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-sky-300"
          >
            <ArrowLeft size={15} />
            전체 전문가
          </button>
        ) : (
          <span className="flex items-center gap-2 text-xs text-slate-400">
            <BookOpen size={16} />
            역할 안내
          </span>
        )}
        <button
          aria-label="전문가 설명 닫기"
          onClick={onClose}
          className="rounded-lg p-2 text-slate-400 hover:bg-white/10"
        >
          <X size={18} />
        </button>
      </header>
      <h2 id="expert-reference-title" className="mb-5 text-lg font-semibold">
        {selected ? expertName(selected) : "전문가 알아보기"}
      </h2>
      {selected ? (
        <ExpertInspector
          key={selected.id}
          expert={selected}
          candidate={candidate}
        />
      ) : (
        <>
          <label className="mb-4 flex items-center gap-2 rounded-lg bg-white/5 px-3 py-3">
            <Search size={15} className="text-slate-500" />
            <input
              aria-label="전문가 검색"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="이름 또는 역할 검색"
              className="min-w-0 w-full bg-transparent text-xs outline-none"
            />
          </label>
          <ul className="space-y-1">
            {filtered.map((expert) => (
              <li key={expert.id}>
                <button
                  onClick={() => onSelect(expert.id)}
                  className="w-full rounded-xl p-3 text-left transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-sky-400"
                >
                  <span className="text-sm">
                    {expertName(expert)}
                    {newExperts.includes(expert.id) && (
                      <span className="ml-2 text-[10px] text-teal-300">
                        신규
                      </span>
                    )}
                  </span>
                  <span className="mt-1 block text-xs text-slate-500">
                    {expertRole(expert.role)} · {expertUniverse(expert)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {!filtered.length && (
            <Empty>검색 조건에 맞는 전문가가 없습니다.</Empty>
          )}
        </>
      )}
    </dialog>
  );
}

function ExpertInspector({
  expert,
  candidate,
}: {
  expert: Expert;
  candidate?: Recipe;
}) {
  const [output, setOutput] = useState<unknown>();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function readOutput() {
    setPending(true);
    setError("");
    try {
      setOutput(
        await request(
          `/api/experts/output?id=${encodeURIComponent(expert.id)}`,
        ),
      );
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "원본 출력 조회 실패",
      );
    } finally {
      setPending(false);
    }
  }
  const refresh = candidate?.refresh_seconds?.[expert.id];
  const purpose = expert.id.startsWith("macrophft_")
    ? "ETH / USDT 시장에서 현금을 유지할지, ETH를 매수·보유할지 판단합니다."
    : (expert.description ?? expertRole(expert.role));
  return (
    <section aria-label="전문가 역할 설명">
      <p className="text-xs text-sky-300">{expertRole(expert.role)}</p>
      <p className="mt-3 text-sm leading-6 text-slate-200">{purpose}</p>
      <dl className="mt-5 grid grid-cols-2 gap-4 border-y border-white/10 py-4 text-xs">
        <div>
          <dt className="text-slate-500">담당 입력</dt>
          <dd className="mt-1">{expertUniverse(expert)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">현재 조합</dt>
          <dd className="mt-1">
            {candidate
              ? candidate.enabled_experts?.includes(expert.id)
                ? "포함됨"
                : "제외됨"
              : "조합 전"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">조립 가능</dt>
          <dd className="mt-1">
            {expert.eligible === undefined
              ? "확인 중"
              : expert.eligible
                ? "가능"
                : "현재 평가 입력 미지원"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">정보 갱신</dt>
          <dd className="mt-1">
            {refresh === undefined ? "별도 설정 없음" : seconds(refresh)}
          </dd>
        </div>
      </dl>
      {expert.universe?.length ? (
        <details className="mt-4 text-xs">
          <summary className="cursor-pointer text-slate-400">
            담당 종목 {number(expert.universe.length)}개
          </summary>
          <p className="mt-2 leading-6">
            {expert.universe.map((symbol) => symbolName(symbol)).join(" · ")}
          </p>
        </details>
      ) : null}
      {expert.error && (
        <p role="alert" className="mt-4 text-xs text-rose-300">
          {expert.error}
        </p>
      )}
      <details className="mt-5 text-xs">
        <summary className="cursor-pointer text-slate-400">
          실행 상태 · 모델 진단
        </summary>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-xs">
          {[
            [
              "실행 상태",
              expert.active ? "사용 중" : expert.loaded ? "적재됨" : "대기",
            ],
            ["파라미터", compactNumber(expert.parameters)],
            [
              "RAM / GPU",
              `${bytes(expert.ram_bytes)} / ${bytes(expert.vram_bytes)}`,
            ],
            ["최근 추론", seconds(expert.last_inference_seconds)],
            ["최근 사용", date(expert.last_used_at)],
            [
              "최근 판단에 선택",
              expert.router_selected === undefined
                ? "기록 없음"
                : expert.router_selected
                  ? "선택됨"
                  : "선택되지 않음",
            ],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-slate-500">{label}</dt>
              <dd className="mt-1">{value}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-slate-500">
          {expert.name} ·{" "}
          {expert.frozen === undefined
            ? "가중치 상태 미수신"
            : expert.frozen
              ? "전문가 가중치 고정"
              : "전문가 가중치 학습 가능"}
          {expert.license ? ` · ${expert.license}` : ""}
        </p>
        <pre className="mt-3 max-h-48 overflow-auto text-[11px] text-slate-400">
          {JSON.stringify(
            {
              input: expert.last_input_shapes ?? expert.input_shapes,
              output: expert.last_output_shape ?? expert.output_shape,
              timing: expert.last_timings,
              model_file_bytes: expert.checkpoint_bytes,
              dtype: expert.dtype,
            },
            null,
            2,
          )}
        </pre>
        <Action
          disabled={pending}
          onClick={() => void readOutput()}
          className="mt-3"
        >
          {pending ? "조회 중" : "원본 출력 조회"}
        </Action>
        {error && (
          <p role="alert" className="mt-3 text-rose-300">
            {error}
          </p>
        )}
        {output !== undefined && (
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-[11px] text-slate-400">
            {JSON.stringify(output, null, 2)}
          </pre>
        )}
      </details>
    </section>
  );
}
