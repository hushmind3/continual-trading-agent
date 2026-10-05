import type { Decision, Fill } from "../api/types";
import {
  actionLabel,
  date,
  money,
  number,
  percent,
  pnlColor,
  seconds,
  symbolName,
} from "../format";
import { Empty } from "./controls";
export function DecisionView({
  decision,
  live = false,
}: {
  decision?: Decision;
  live?: boolean;
}) {
  if (!decision) return <Empty>아직 판단이 없습니다.</Empty>;
  return (
    <section className="py-4">
      <div className="flex flex-wrap items-baseline gap-4">
        <h2 className="text-2xl font-semibold">
          {decision.symbol ? symbolName(decision.symbol) : "종목 정보 미수신"}
        </h2>
        <strong
          className={`text-3xl ${decision.action === "BUY" ? "text-rose-300" : decision.action === "SELL" ? "text-sky-300" : "text-slate-300"}`}
        >
          {actionLabel(decision.action)}
        </strong>
      </div>
      <p className="mt-4 text-xl tabular-nums">
        {decision.current_weight === undefined
          ? "현재 비중 미수신"
          : percent(decision.current_weight)}{" "}
        <span className="mx-2 text-slate-500">→</span>{" "}
        {percent(decision.target_weight)}
        <span className="ml-3 text-xs text-slate-500">목표</span>
      </p>
      <p className="mt-3 text-xs text-slate-500">
        {live ? "최근 판단" : "저장된 최근 판단"} ·{" "}
        <time title={decision.as_of ?? decision.date}>
          {date(decision.as_of ?? decision.date)}
        </time>{" "}
        · {seconds(decision.seconds)}
      </p>
      {decision.cash_weight !== undefined && (
        <p className="mt-2 text-xs text-slate-400">
          목표 현금 {percent(decision.cash_weight)}
        </p>
      )}
    </section>
  );
}
export function FillList({ fills }: { fills?: Fill[] }) {
  if (!fills?.length) return <Empty>아직 가상 체결이 없습니다.</Empty>;
  return (
    <div className="overflow-auto">
      <table className="w-full text-left text-xs">
        <thead className="text-slate-500">
          <tr>
            {[
              "시각",
              "종목",
              "매매",
              "계좌 수량",
              "체결가",
              "수수료",
              "실현손익",
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
          {fills
            .slice(-30)
            .reverse()
            .map((fill, index) => (
              <tr
                key={`${fill.date}-${index}`}
                className="border-t border-white/5"
              >
                <td className="whitespace-nowrap px-3 py-3" title={fill.date}>
                  {date(fill.date)}
                </td>
                <td className="px-3">{symbolName(fill.symbol)}</td>
                <td
                  className={
                    fill.action === "BUY" ? "text-rose-300" : "text-sky-300"
                  }
                >
                  {actionLabel(fill.action)}
                </td>
                <td className="px-3 text-right tabular-nums">
                  {number(fill.quantity, 6)}
                </td>
                <td className="px-3 text-right tabular-nums">
                  {fill.currency
                    ? money(fill.price, fill.currency)
                    : number(fill.price, 6)}
                </td>
                <td className="px-3 text-right">
                  {fill.currency
                    ? money(fill.fee, fill.currency)
                    : number(fill.fee, 6)}
                </td>
                <td
                  className={`px-3 text-right ${pnlColor(fill.realized_pnl)}`}
                >
                  {fill.currency
                    ? money(fill.realized_pnl, fill.currency)
                    : number(fill.realized_pnl, 6)}
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
