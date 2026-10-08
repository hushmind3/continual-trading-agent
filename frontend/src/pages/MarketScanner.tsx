import { useCallback, useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { request } from "../data/api";
import { useOperations } from "../data/Operations";
import type { Instrument } from "../data/types";
import {
  Drawer,
  Empty,
  ErrorMessage,
  Meter,
  Sparkline,
  inputClass,
} from "../ui/Primitives";
import { date, marketName, money, number, percent } from "../ui/format";
import { ControlButton } from "../ui/ControlButton";

const displayName = (item: Instrument) =>
  item.name ||
  (
    {
      "^DJI": "다우존스",
      "^FTSE": "FTSE 100",
      "^IXIC": "나스닥 종합",
      "^GSPC": "S&P 500",
    } as Record<string, string>
  )[item.symbol.replace(/_+$/, "")] ||
  item.symbol;
function price(item: Instrument) {
  const value=item.latest_tick?.price??item.quote?.close;
  if (value==null) return "미수신";
  return ["equity", "etf"].includes(item.asset_class)&&['KRX','KOSDAQ','US','NASDAQ','NYSE','AMEX'].includes(item.market)
    ? money(
        value,
        ["KRX", "KOSDAQ"].includes(item.market) ? "KRW" : "USD",
      )
    : number(value, 3);
}
function change(item: Instrument) {
  const history = item.history;
  if(item.latest_tick&&history.length&&history.at(-1)!.close>0)return item.latest_tick.price/history.at(-1)!.close-1;
  return history.length > 1 && history.at(-2)!.close > 0
    ? history.at(-1)!.close / history.at(-2)!.close - 1
    : null;
}

export function MarketScanner() {
  const { state } = useOperations();
  const [items, setItems] = useState<Instrument[]>([]),
    [search, setSearch] = useState(""),
    [market, setMarket] = useState("all"),
    [sort, setSort] = useState("fresh"),
    [selected, setSelected] = useState<string | null>(null),
    [error, setError] = useState(""),
    [limit, setLimit] = useState(80);
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const data = await request<{ instruments: Instrument[] }>("markets");
        if (active) {
          setItems(data.instruments);
          setError("");
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "시세 조회 실패");
      }
    };
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  const list = useMemo(
    () =>
      items
        .filter(
          (i) =>
            (market === "all" || i.market === market) &&
            `${displayName(i)} ${i.symbol}`
              .toLowerCase()
              .includes(search.toLowerCase()),
        )
        .sort((a, b) =>
          sort === "change"
            ? Math.abs(change(b) ?? 0) - Math.abs(change(a) ?? 0)
            : (b.quote?.date ?? "").localeCompare(a.quote?.date ?? ""),
        ),
    [items, market, search, sort],
  );
  const selectedItem = items.find((i) => i.symbol === selected),
    close = useCallback(() => setSelected(null), []);
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <label className="relative min-w-48 flex-1 sm:max-w-xs">
            <Search
              size={16}
              className="absolute left-3 top-3 text-slate-400"
            />
            <input
              className={`${inputClass} pl-9`}
              aria-label="종목 검색"
              placeholder="종목 이름 또는 코드"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setLimit(80);
              }}
            />
          </label>
          <select
            className={inputClass.replace("w-full", "w-auto")}
            aria-label="시장 필터"
            value={market}
            onChange={(e) => {
              setMarket(e.target.value);
              setLimit(80);
            }}
          >
            <option value="all">모든 시장</option>
            {[...new Set(items.map((i) => i.market))].sort().map((m) => (
              <option key={m} value={m}>
                {marketName(m)}
              </option>
            ))}
          </select>
          <select
            aria-label="종목 정렬"
            className={inputClass.replace("w-full", "w-auto")}
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="fresh">최신 관측 순</option>
            <option value="change">변화가 큰 순</option>
          </select>
        </div>
        <ControlButton name="feed" label="시세" compact />
      </div>
      {error && <ErrorMessage message={error} />}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>{number(list.length, 0)}개 종목</span>
        <span>변화는 직전 관측 대비 · 행을 누르면 상세</span>
      </div>
      <section className="max-h-[70dvh] overflow-auto rounded-2xl bg-white shadow-sm ring-1 ring-slate-200/50">
        <table className="w-full text-left">
          <thead className="sticky top-0 z-10 bg-white text-xs text-slate-400">
            <tr>
              <th className="px-4 py-4 font-medium sm:px-5">종목</th>
              <th className="px-3 py-4 text-right font-medium">가격</th>
              <th className="px-3 py-4 text-right font-medium">변화</th>
              <th className="hidden px-4 py-4 font-medium md:table-cell">
                관측 추이
              </th>
              <th className="hidden px-4 py-4 font-medium lg:table-cell">
                현재 판단
              </th>
              <th className="hidden px-4 py-4 text-right font-medium xl:table-cell">
                관측 시각
              </th>
            </tr>
          </thead>
          <tbody>
            {list.slice(0, limit).map((item) => {
              const delta = change(item);
              return (
                <tr
                  key={item.symbol}
                  tabIndex={0}
                  aria-label={`${displayName(item)} 상세`}
                  aria-selected={selected === item.symbol}
                  onClick={() => setSelected(item.symbol)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelected(item.symbol);
                    }
                  }}
                  className={`cursor-pointer border-t border-slate-50 outline-none transition hover:bg-slate-50 focus-visible:bg-blue-50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-400 ${selected === item.symbol ? "bg-blue-50/70" : ""}`}
                >
                  <td className="px-4 py-3.5 sm:px-5">
                    <div className="text-sm font-semibold text-slate-700">
                      {displayName(item)}
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400">
                      {item.symbol} · {marketName(item.market)}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3.5 text-right text-sm font-medium tabular-nums">
                    {price(item)}
                  </td>
                  <td
                    className={`whitespace-nowrap px-3 py-3.5 text-right text-sm font-semibold tabular-nums ${delta == null ? "text-slate-300" : delta >= 0 ? "text-rose-500" : "text-blue-500"}`}
                  >
                    {delta == null
                      ? "대기"
                      : `${delta > 0 ? "+" : ""}${percent(delta)}`}
                  </td>
                  <td className="hidden w-28 px-4 py-3.5 md:table-cell">
                    {item.history.length > 1 ? (
                      <Sparkline
                        values={item.history.map((v) => v.close)}
                        height={28}
                        up={(delta ?? 0) >= 0}
                      />
                    ) : (
                      <span className="text-xs text-slate-300">관측 대기</span>
                    )}
                  </td>
                  <td className="hidden px-4 py-3.5 lg:table-cell">
                    {item.decision ? (
                      <div>
                        <span
                          className={`text-xs font-semibold ${item.decision.action === "BUY" ? "text-rose-500" : item.decision.action === "SELL" ? "text-blue-500" : "text-slate-400"}`}
                        >
                          {item.decision.action === "BUY"
                            ? "매수"
                            : item.decision.action === "SELL"
                              ? "매도"
                              : "보유"}
                        </span>
                        <div className="mt-1 text-xs tabular-nums text-slate-400">
                          {percent(item.decision.current_weight)} →{" "}
                          {percent(item.decision.target_weight)}
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-300">판단 대기</span>
                    )}
                  </td>
                  <td className="hidden whitespace-nowrap px-4 py-3.5 text-right text-xs tabular-nums text-slate-400 xl:table-cell">
                    <time title={item.latest_tick?.date ?? item.quote?.date}>
                          {date(item.latest_tick?.date??item.quote?.date)}
                    </time>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!list.length && (
          <Empty
            title={
              search ? "검색 결과가 없습니다." : "종목을 불러오는 중입니다."
            }
          />
        )}{" "}
        {list.length > limit && (
          <button
            className="w-full border-t border-slate-100 py-4 text-xs font-semibold text-blue-600 hover:bg-blue-50"
            onClick={() => setLimit((v) => v + 80)}
          >
            다음 종목 더 보기
          </button>
        )}
      </section>
      <Drawer
        title={selectedItem ? displayName(selectedItem) : "종목 상세"}
        open={Boolean(selectedItem)}
        onClose={close}
      >
        {selectedItem && (
          <div className="space-y-6">
            <div>
              <div className="text-xs text-slate-400">
                {selectedItem.symbol} · {marketName(selectedItem.market)}
              </div>
              <div className="mt-2 text-3xl font-bold tabular-nums">
                {price(selectedItem)}
              </div>
              <div className="mt-5">
                <Sparkline
                  values={selectedItem.history.map((v) => v.close)}
                  height={100}
                  up={(change(selectedItem) ?? 0) >= 0}
                />
              </div>
            </div>
            {selectedItem.decision ? (
              <section className="rounded-2xl bg-blue-50 p-5">
                <h3 className="text-sm font-bold text-blue-900">
                  MoE가 정한 목표
                </h3>
                <div className="mt-3 flex items-end justify-between">
                  <span className="text-sm text-blue-700">
                    현재 {percent(selectedItem.decision.current_weight)}
                  </span>
                  <span className="text-2xl font-bold text-blue-700">
                    {percent(selectedItem.decision.target_weight)}
                  </span>
                </div>
                <div className="mt-4">
                  <Meter value={selectedItem.decision.target_weight * 100} />
                </div>
                <p className="mt-3 text-xs text-blue-500">
                  {date(selectedItem.decision.as_of)} 판단 · 위험검사 후 목표
                  비중
                </p>
              </section>
            ) : (
              <Empty title="이 종목의 실제 판단은 아직 없습니다." />
            )}
            {selectedItem.quote && (
              <div>
                <h3 className="mb-4 text-sm font-semibold">관측 정보</h3>
                <dl className="grid grid-cols-2 gap-5 text-sm">
                  {[
                    ["고가", number(selectedItem.quote.high, 3)],
                    ["저가", number(selectedItem.quote.low, 3)],
                    ["거래량", number(selectedItem.quote.volume, 0)],
                    ["수신 시각", date(selectedItem.quote.date)],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="text-xs text-slate-400">{label}</dt>
                      <dd className="mt-1 font-medium tabular-nums">{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
            {selectedItem.required_by?.length ? (
              <div className="rounded-xl bg-slate-50 p-4 text-xs leading-5 text-slate-500">
                이 종목은{" "}
                {selectedItem.required_by
                  .map(
                    (id) => state?.experts.find((e) => e.id === id)?.name ?? id,
                  )
                  .join(", ")}
                의 원래 입력 종목입니다.
              </div>
            ) : null}
          </div>
        )}
      </Drawer>
    </div>
  );
}
