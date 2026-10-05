import type { Expert, Recipe } from "../../api/types";
import { candidateChanges, date, number } from "../../format";

export function AssemblyQueue({
  recipes,
  experts,
}: {
  recipes: Recipe[];
  experts: Expert[];
}) {
  return (
    <details className="rounded-xl border border-white/7 px-4 py-3">
      <summary className="cursor-pointer text-xs text-slate-300">
        다음 조합{" "}
        <span className="ml-2 text-slate-500">{number(recipes.length)}</span>
      </summary>
      {recipes.length ? (
        <ol className="mt-3 space-y-3">
          {recipes.map((recipe, index) => (
            <li
              key={recipe.candidate_id}
              className="border-t border-white/5 pt-3 text-xs"
            >
              <p className="text-slate-400">
                {index + 1}번째 대기 · 전문가{" "}
                {number(recipe.enabled_experts?.length)}개
              </p>
              <p className="mt-1 leading-5 text-slate-200">
                {candidateChanges(recipe, experts).join(" · ")}
              </p>
              {recipe.created_at && (
                <p className="mt-1 text-[10px] text-slate-500">
                  {date(recipe.created_at)}
                </p>
              )}
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-xs text-slate-500">
          대기 중인 조합이 없습니다.
        </p>
      )}
    </details>
  );
}
