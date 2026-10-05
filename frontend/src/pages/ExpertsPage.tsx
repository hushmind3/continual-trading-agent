import { useEffect, useState } from "react";
import { useWorkspace } from "../state/Workspace";
import { request } from "../api/client";
import { Empty, QueryState } from "../components/controls";
import { bytes, date, number, seconds } from "../format";
export function ExpertsPage() {
  const { registry } = useWorkspace();
  const [selectedId, setSelectedId] = useState("");
  const [search, setSearch] = useState("");
  const [raw, setRaw] = useState<unknown>();
  const [rawError, setRawError] = useState("");
  const [rawPending, setRawPending] = useState(false);
  const experts = (registry.data?.experts ?? []).filter((expert) =>
    `${expert.name} ${expert.role}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const selected =
    experts.find((expert) => expert.id === selectedId) ?? experts[0];
  useEffect(() => {
    setRaw(undefined);
    setRawError("");
    setRawPending(false);
  }, [selected?.id]);
  async function readOutput() {
    if (!selected) return;
    const id = selected.id;
    setRawPending(true);
    setRawError("");
    try {
      const value = await request(
        `/api/experts/output?id=${encodeURIComponent(id)}`,
      );
      setRaw({ expert_id: id, data: value });
    } catch (error) {
      setRawError(
        error instanceof Error ? error.message : "원본 출력 조회 실패",
      );
    } finally {
      setRawPending(false);
    }
  }
  return (
    <>
      <QueryState {...registry} />
      <input
        aria-label="전문가 검색"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="전문가 이름 또는 역할"
        className="mb-6 w-full rounded-lg bg-white/5 px-4 py-3 text-sm"
      />
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="overflow-auto">
          {experts.length ? (
            <table className="w-full text-left text-xs">
              <thead className="text-slate-500">
                <tr>
                  {[
                    "전문가 / 역할",
                    "상태",
                    "파라미터",
                    "RAM / GPU",
                    "최근 추론",
                  ].map((label) => (
                    <th
                      key={label}
                      className="whitespace-nowrap px-3 py-3 font-medium"
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {experts.map((expert) => (
                  <tr
                    key={expert.id}
                    tabIndex={0}
                    aria-selected={selected?.id === expert.id}
                    onClick={() => setSelectedId(expert.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedId(expert.id);
                      }
                    }}
                    className={`cursor-pointer border-t border-white/5 outline-none hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 ${selected?.id === expert.id ? "bg-sky-400/10" : ""}`}
                  >
                    <td className="px-3 py-4">
                      <strong className="font-medium">{expert.name}</strong>
                      <p className="mt-1 text-slate-500">{expert.role}</p>
                    </td>
                    <td className="px-3 text-slate-400">
                      {expert.active ? "활성" : expert.loaded ? "적재" : "대기"}
                    </td>
                    <td className="px-3 text-right tabular-nums">
                      {number(expert.parameters)}
                    </td>
                    <td className="whitespace-nowrap px-3 text-right">
                      {bytes(expert.ram_bytes)} / {bytes(expert.vram_bytes)}
                    </td>
                    <td className="px-3 text-right tabular-nums">
                      {seconds(expert.last_inference_seconds)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty>전문가 목록이 없습니다.</Empty>
          )}
        </div>
        {selected && (
          <aside className="rounded-2xl bg-[#1a2434] p-5">
            <h2 className="text-lg font-semibold">{selected.name}</h2>
            <p className="mt-2 text-sm text-slate-400">{selected.role}</p>
            <dl className="mt-6 space-y-3 text-xs">
              <div className="flex justify-between">
                <dt>현재 활성</dt>
                <dd>{selected.active ? "예" : "아니요"}</dd>
              </div>
              <div className="flex justify-between">
                <dt>모델 적재</dt>
                <dd>{selected.loaded ? "예" : "아니요"}</dd>
              </div>
              <div className="flex justify-between">
                <dt>최근 판단에 선택</dt>
                <dd>{selected.router_selected ? "예" : "아니요"}</dd>
              </div>
              <div className="flex justify-between">
                <dt>최근 사용</dt>
                <dd>{date(selected.last_used_at)}</dd>
              </div>
            </dl>
            {selected.error && (
              <p role="alert" className="mt-4 text-xs text-rose-300">
                {selected.error}
              </p>
            )}
            <details className="mt-6 text-xs">
              <summary className="cursor-pointer text-slate-400">
                입출력 · 원본 정보
              </summary>
              <pre className="mt-4 max-h-60 overflow-auto text-[11px] text-slate-500">
                {JSON.stringify(
                  {
                    input: selected.last_input_shapes ?? selected.input_shapes,
                    output: selected.last_output_shape ?? selected.output_shape,
                    timing: selected.last_timings,
                  },
                  null,
                  2,
                )}
              </pre>
              <button
                disabled={rawPending}
                onClick={() => void readOutput()}
                className="my-4 text-sky-300"
              >
                {rawPending ? "조회 중" : "원본 출력 조회"}
              </button>
              {rawError && <p className="text-rose-300">{rawError}</p>}
              {raw !== undefined &&
                (raw as { expert_id: string }).expert_id === selected.id && (
                  <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-[11px] text-slate-400">
                    {JSON.stringify(raw, null, 2)}
                  </pre>
                )}
            </details>
          </aside>
        )}
      </div>
    </>
  );
}
