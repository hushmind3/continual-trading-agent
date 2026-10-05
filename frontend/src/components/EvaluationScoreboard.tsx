import type { ScorePair, Score } from "../api/types";
import { money, number, percent, pnlColor, seconds } from "../format";
import { Empty } from "./controls";
const fields: { label: string; read: (score: Score) => string }[] = [
  { label: "수익률", read: (score) => percent(score.net_return) },
  { label: "최대 손실폭", read: (score) => percent(score.max_drawdown) },
  { label: "수수료", read: (score) => money(score.fees, "USD") },
  { label: "슬리피지", read: (score) => money(score.slippage, "USD") },
  { label: "체결 수", read: (score) => number(score.trades) },
  { label: "판단 수", read: (score) => number(score.decisions) },
  { label: "실행 시간", read: (score) => seconds(score.seconds) },
];
export function EvaluationScoreboard({
  pair,
  label,
}: {
  pair?: ScorePair;
  label: string;
}) {
  return (
    <section className="mt-6">
      <div className="mb-4 flex flex-wrap justify-between gap-3">
        <h2 className="text-sm font-semibold">{label}</h2>
        {pair?.delta !== undefined && (
          <p className={`text-sm ${pnlColor(pair.delta)}`}>
            Champion 대비 {number(pair.delta * 100, 3)}%p
          </p>
        )}
      </div>
      {pair ? (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500">
              <th className="pb-4 text-left font-normal">동일 구간 비교</th>
              <th className="pb-4 text-right font-normal">Champion</th>
              <th className="pb-4 text-right font-normal">Candidate</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.label} className="border-t border-white/5">
                <th className="py-3 text-left text-xs font-normal text-slate-400">
                  {field.label}
                </th>
                <td className="text-right tabular-nums">
                  {pair.champion ? field.read(pair.champion) : "평가 대기"}
                </td>
                <td className="text-right tabular-nums">
                  {pair.candidate ? field.read(pair.candidate) : "평가 대기"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <Empty>평가 결과가 아직 없습니다.</Empty>
      )}
    </section>
  );
}
