import { useState } from "react";
import { useWorkspace } from "../state/Workspace";
import { DecisionView } from "../components/Execution";
import { Empty, QueryState } from "../components/controls";
import {
  date,
  number,
  numeric,
  percent,
  pnlColor,
  symbolName,
} from "../format";
const groupLabels: Record<string, string> = {
  korea: "한국",
  us: "미국",
  crypto: "코인",
  global: "세계 시장",
  forex: "외환",
  indices: "지수",
  bonds: "채권",
};
export function MarketsPage() {
  const { status } = useWorkspace();
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("all");
  const [freshOnly, setFreshOnly] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [sort, setSort] = useState("name");
  const instruments = status.data?.instruments ?? [];
  const groups = Array.from(
    new Set(instruments.map((item) => item.group ?? item.market ?? "other")),
  );
  const filtered = instruments
    .filter(
      (item) =>
        (group === "all" || (item.group ?? item.market) === group) &&
        (!freshOnly || item.fresh) &&
        `${item.symbol} ${symbolName(item.symbol, item.name)}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "volume"
        ? (numeric(b.quote?.volume) ?? -1) - (numeric(a.quote?.volume) ?? -1)
        : symbolName(a.symbol, a.name).localeCompare(
            symbolName(b.symbol, b.name),
          ),
    );
  const selected =
    filtered.find((item) => item.symbol === symbol) ?? filtered[0];
  return (
    <>
      <QueryState {...status} />
      <div className="sticky top-[68px] z-10 mb-5 flex flex-wrap gap-3 bg-[#101725] py-3">
        <input
          aria-label="종목 검색"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="종목 이름 또는 코드"
          className="min-w-0 flex-1 rounded-lg bg-white/5 px-4 py-2.5 text-sm"
        />
        <select
          aria-label="시장 선택"
          value={group}
          onChange={(event) => setGroup(event.target.value)}
          className="rounded-lg bg-[#243044] px-3 text-sm"
        >
          <option value="all">전체 시장</option>
          {groups.map((value) => (
            <option key={value} value={value}>
              {groupLabels[value] ?? value}
            </option>
          ))}
        </select>
        <select
          aria-label="정렬"
          value={sort}
          onChange={(event) => setSort(event.target.value)}
          className="rounded-lg bg-[#243044] px-3 text-sm"
        >
          <option value="name">이름순</option>
          <option value="volume">거래량순</option>
        </select>
        <button
          aria-pressed={freshOnly}
          onClick={() => setFreshOnly(!freshOnly)}
          className={`rounded-lg px-3 text-xs ${freshOnly ? "bg-sky-400 text-slate-950" : "bg-white/5 text-slate-400"}`}
        >
          최신 수신만
        </button>
      </div>
      <p className="mb-3 text-xs text-slate-500">
        {filtered.length}종목 ·{" "}
        {status.data?.feed_running ? "수집 중" : "수집 정지"}
      </p>
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="max-h-[65vh] overflow-auto">
          {filtered.length ? (
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-[#101725] text-slate-500">
                <tr>
                  {[
                    "종목",
                    "현재가",
                    "시가 대비",
                    "거래량",
                    "판단",
                    "수신",
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
                {filtered.map((item) => {
                  const close = numeric(item.quote?.close),
                    open = numeric(item.quote?.open);
                  const change =
                    close !== undefined && open ? close / open - 1 : undefined;
                  return (
                    <tr
                      key={item.symbol}
                      tabIndex={0}
                      aria-selected={selected?.symbol === item.symbol}
                      onClick={() => setSymbol(item.symbol)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSymbol(item.symbol);
                        }
                      }}
                      className={`cursor-pointer border-t border-white/5 outline-none hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 ${selected?.symbol === item.symbol ? "bg-sky-400/10" : ""}`}
                    >
                      <td className="px-3 py-4">
                        <strong className="font-medium">
                          {symbolName(item.symbol, item.name)}
                        </strong>
                        <p className="mt-1 text-[10px] text-slate-500">
                          {item.symbol}
                        </p>
                      </td>
                      <td className="px-3 text-right tabular-nums">
                        {number(close, 4)}
                      </td>
                      <td
                        className={`px-3 text-right tabular-nums ${pnlColor(change)}`}
                      >
                        {change === undefined ? "미수신" : percent(change)}
                      </td>
                      <td className="px-3 text-right tabular-nums">
                        {number(item.quote?.volume)}
                      </td>
                      <td className="px-3">
                        {item.decision?.action ?? "대기"}
                      </td>
                      <td
                        className="px-3 text-[10px] text-slate-500"
                        title={String(item.quote?.date ?? "")}
                      >
                        {item.fresh
                          ? "최신"
                          : date(String(item.quote?.date ?? ""))}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <Empty>조건에 맞는 종목이 없습니다.</Empty>
          )}
        </div>
        {selected && (
          <aside className="rounded-2xl bg-[#1a2434] p-5">
            <h2 className="font-semibold">
              {symbolName(selected.symbol, selected.name)}
            </h2>
            <p className="mt-2 text-xs text-slate-500">
              {selected.market} · {selected.fresh ? "최신 시세" : "저장된 시세"}
            </p>
            <DecisionView decision={selected.decision ?? undefined} />
            <dl className="space-y-3 border-t border-white/10 pt-4 text-xs">
              {[
                ["고가", selected.quote?.high],
                ["저가", selected.quote?.low],
                ["매수 호가", selected.quote?.bid],
                ["매도 호가", selected.quote?.ask],
              ]
                .filter(([, value]) => numeric(value) !== undefined)
                .map(([label, value]) => (
                  <div key={label} className="flex justify-between">
                    <dt className="text-slate-500">{label}</dt>
                    <dd>{number(value, 4)}</dd>
                  </div>
                ))}
            </dl>
          </aside>
        )}
      </div>
    </>
  );
}
