import { useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Wallet } from "lucide-react";
import { useOperations } from "../data/Operations";
import type { Currency } from "../data/types";
import { ControlButton } from "../ui/ControlButton";
import { Empty, Meter, Skeleton, Sparkline, Tabs } from "../ui/Primitives";
import { date, money, number, percent } from "../ui/format";

export function PortfolioWorkspace() {
  const { state } = useOperations();
  const [currency, setCurrency] = useState<Currency>("USD"),
    [tab, setTab] = useState("positions");
  if (!state) return <Skeleton />;
  const book = state.account?.books[currency],
    history = state.equity_history[currency] ?? [],
    fills =
      state.account?.fills
        .filter((f) => f.currency === currency)
        .slice(-30)
        .reverse() ?? [];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs
          items={[
            { id: "USD", label: "달러 계좌" },
            { id: "KRW", label: "원화 계좌" },
          ]}
          value={currency}
          onChange={(v) => setCurrency(v as Currency)}
        />
        <ControlButton name="paper" label="가상체결" />
      </div>
      {!book ? (
        <div className="rounded-2xl bg-white">
          <Empty
            title="MoE를 실행하면 가상계좌를 불러옵니다."
            detail="실제 주문을 보내지 않습니다."
          />
        </div>
      ) : (
        <>
          <section className="grid gap-8 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200/50 lg:grid-cols-[1fr_1.15fr]">
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Wallet size={17} />총 평가금액
              </div>
              <div className="mt-3 text-3xl font-bold tabular-nums tracking-tight sm:text-4xl">
                {money(book.equity, currency)}
              </div>
              <p
                className={`mt-3 flex items-center gap-1.5 text-sm font-semibold ${book.pnl >= 0 ? "text-rose-500" : "text-blue-500"}`}
              >
                {book.pnl >= 0 ? (
                  <ArrowUpRight size={16} />
                ) : (
                  <ArrowDownLeft size={16} />
                )}{" "}
                {book.pnl > 0 ? "+" : ""}
                {money(book.pnl, currency)}{" "}
                <span className="font-medium">
                  ({percent(book.return_rate)})
                </span>
              </p>
              <div className="mt-6 flex gap-6 text-xs text-slate-400">
                <span>
                  초기 금액{" "}
                  <b className="ml-1 font-medium text-slate-600">
                    {money(book.initial_cash, currency)}
                  </b>
                </span>
                <span>
                  체결{" "}
                  <b className="ml-1 text-slate-600">
                    {number(book.trade_count, 0)}회
                  </b>
                </span>
              </div>
            </div>
            <div>
              <div className="mb-3 flex items-center justify-between text-xs text-slate-400">
                <span>실제 계좌 평가 기록</span>
                <span>
                  {history.length
                    ? date(history.at(-1)?.as_of)
                    : "첫 관측 대기"}
                </span>
              </div>
              <Sparkline
                values={history.map((h) => h.equity)}
                up={book.pnl >= 0}
                height={110}
              />
              <div className="mt-5 flex justify-between text-xs text-slate-500">
                <span>현금 {money(book.cash, currency)}</span>
                <span>보유자산 {money(book.equity - book.cash, currency)}</span>
              </div>
              <div className="mt-2">
                <Meter
                  value={
                    book.equity > 0
                      ? ((book.equity - book.cash) / book.equity) * 100
                      : 0
                  }
                  color="bg-blue-500"
                />
              </div>
            </div>
          </section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Tabs
              items={[
                { id: "positions", label: "보유자산" },
                { id: "fills", label: "체결 기록" },
              ]}
              value={tab}
              onChange={setTab}
            />
            <span className="text-xs text-slate-400">
              누적 비용{" "}
              {money(
                book.fees + book.slippage + book.spread + book.sell_tax,
                currency,
              )}
            </span>
          </div>
          {tab === "positions" ? (
            book.positions.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {book.positions.map((p) => (
                  <article
                    key={p.symbol}
                    className="rounded-2xl bg-white p-5 transition hover:shadow-sm"
                  >
                    <div className="flex justify-between gap-3">
                      <div>
                        <b className="text-base">{p.symbol}</b>
                        <p className="mt-1 text-xs text-slate-400">
                          {number(p.quantity, 4)}주 · 평균{" "}
                          {money(p.average_cost, currency)}
                        </p>
                      </div>
                      <span className="text-sm font-semibold tabular-nums">
                        {percent(p.value / book.equity)}
                      </span>
                    </div>
                    <div className="mt-5 flex items-end justify-between">
                      <b className="text-xl tabular-nums">
                        {money(p.value, currency)}
                      </b>
                      <span
                        className={`text-sm font-semibold ${p.pnl >= 0 ? "text-rose-500" : "text-blue-500"}`}
                      >
                        {p.pnl > 0 ? "+" : ""}
                        {money(p.pnl, currency)}
                      </span>
                    </div>
                    <div className="mt-4">
                      <Meter value={(p.value / book.equity) * 100} />
                    </div>
                    <a
                      className="mt-4 block text-xs text-slate-400 hover:text-blue-600"
                      href="#markets"
                    >
                      현재 시장 상태 보기 →
                    </a>
                  </article>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl bg-white">
                <Empty
                  title="현재 보유자산이 없습니다."
                  detail="가상체결을 시작하고 다음 완료 시세가 들어오면 주문을 처리합니다."
                />
              </div>
            )
          ) : fills.length ? (
            <div className="overflow-x-auto rounded-2xl bg-white">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-100 text-xs text-slate-400">
                  <tr>
                    {["시각", "종목", "행동", "수량", "체결가", "수수료"].map(
                      (v) => (
                        <th
                          key={v}
                          className="whitespace-nowrap px-5 py-4 font-medium"
                        >
                          {v}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {fills.map((fill, i) => (
                    <tr
                      key={i}
                      className="border-b border-slate-50 last:border-0"
                    >
                      <td className="whitespace-nowrap px-5 py-4 text-xs text-slate-400">
                        {date(fill.date)}
                      </td>
                      <td className="px-5 py-4 font-semibold">{fill.symbol}</td>
                      <td
                        className={`px-5 py-4 font-medium ${fill.action === "BUY" ? "text-rose-500" : "text-blue-500"}`}
                      >
                        {fill.action === "BUY" ? "매수" : "매도"}
                      </td>
                      <td className="px-5 py-4 tabular-nums">
                        {number(fill.quantity, 4)}
                      </td>
                      <td className="px-5 py-4 tabular-nums">
                        {money(fill.price, currency)}
                      </td>
                      <td className="px-5 py-4 tabular-nums text-slate-400">
                        {money(fill.fee ?? 0, currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-2xl bg-white">
              <Empty title="아직 체결 기록이 없습니다." />
            </div>
          )}
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-400">
            <span>체결 방식: 다음 완료 시세</span>
            <span>설정 수수료 {percent(state.settings.risk.fee)}</span>
            <span>
              설정 가격 미끄러짐 {percent(state.settings.risk.slippage)}
            </span>
            <span>환전 없이 통화별 분리 계산</span>
          </div>
        </>
      )}
    </div>
  );
}
