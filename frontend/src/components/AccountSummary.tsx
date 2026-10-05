import { useState } from "react";
import type { Book, Currency } from "../api/types";
import {
  money,
  netPnl,
  number,
  percent,
  pnlColor,
  positions,
  symbolName,
} from "../format";
import { Empty } from "./controls";

export function AccountSummary({
  books,
}: {
  books?: Partial<Record<Currency, Book>>;
}) {
  const [currency, setCurrency] = useState<Currency>("USD");
  const book = books?.[currency];
  const pnl = book ? netPnl(book) : undefined;
  const held = book ? positions(book) : [];
  return (
    <section className="mt-5 border-t border-white/10 pt-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm text-slate-300">가상계좌</h3>
        <div className="flex gap-1">
          {(["USD", "KRW"] as const).map((value) => (
            <button
              key={value}
              onClick={() => setCurrency(value)}
              aria-pressed={currency === value}
              className={`rounded-md px-2 py-1 text-[11px] ${currency === value ? "bg-white/10 text-white" : "text-slate-500"}`}
            >
              {value}
            </button>
          ))}
        </div>
      </div>
      {book ? (
        <>
          <p className="text-2xl font-semibold tabular-nums">
            {money(book.equity, currency)}
          </p>
          <p className={`mt-1 text-sm tabular-nums ${pnlColor(pnl)}`}>
            {money(pnl, currency)}
            {book.initial_cash
              ? ` · ${percent(Number(pnl) / book.initial_cash)}`
              : ""}
          </p>
          <dl className="mt-4 space-y-2 text-xs">
            <div className="flex justify-between">
              <dt className="text-slate-500">현금</dt>
              <dd>{money(book.cash, currency)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">보유 / 체결</dt>
              <dd>
                {held.length}종목 / {number(book.trade_count)}회
              </dd>
            </div>
          </dl>
          <details className="mt-4 text-xs">
            <summary className="cursor-pointer text-slate-400">
              포지션 · 손익 상세
            </summary>
            <div className="mt-3 space-y-3">
              {held.length ? (
                held.map((p) => (
                  <div key={p.symbol} className="border-b border-white/5 pb-3">
                    <div className="flex justify-between">
                      <strong>{symbolName(p.symbol)}</strong>
                      <span>{number(p.quantity, 6)} 계좌 수량</span>
                    </div>
                    <div className="mt-2 flex justify-between text-slate-400">
                      <span>평단 {money(p.average_cost, currency)}</span>
                      <span className={pnlColor(p.unrealized_pnl)}>
                        {money(p.unrealized_pnl, currency)}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <Empty>보유 종목 없음</Empty>
              )}
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt>수수료</dt>
                  <dd>{money(book.fees, currency)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>슬리피지</dt>
                  <dd>{money(book.slippage, currency)}</dd>
                </div>
                {book.realized_pnl !== undefined && (
                  <div className="flex justify-between">
                    <dt>실현손익</dt>
                    <dd>{money(book.realized_pnl, currency)}</dd>
                  </div>
                )}
              </dl>
            </div>
          </details>
        </>
      ) : (
        <Empty>계좌 상태를 아직 받지 못했습니다.</Empty>
      )}
    </section>
  );
}
