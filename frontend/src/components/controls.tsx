import type { ButtonHTMLAttributes, ReactNode } from "react";
import { useWorkspace } from "../state/Workspace";
export function Action({
  children,
  primary = false,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { primary?: boolean }) {
  return (
    <button
      {...props}
      className={`flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-150 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100 ${primary ? "bg-sky-400 text-slate-950 hover:bg-sky-300" : "bg-white/8 text-slate-200 hover:bg-white/15"} ${className}`}
    >
      {children}
    </button>
  );
}
export function Switch({
  on,
  onChange,
  label,
  disabled = false,
}: {
  on: boolean;
  onChange: () => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={disabled}
      onClick={onChange}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${on ? "bg-sky-400" : "bg-slate-600"}`}
    >
      <span
        className={`absolute top-1 size-4 rounded-full bg-white shadow-sm transition-transform ${on ? "left-1 translate-x-5" : "left-1"}`}
      />
    </button>
  );
}
export function Legend({ children, on }: { children: ReactNode; on: boolean }) {
  return (
    <span
      className={`flex items-center gap-2 text-xs ${on ? "text-emerald-300" : "text-slate-400"}`}
    >
      <span
        className={`size-1.5 rounded-full ${on ? "bg-emerald-300 shadow-[0_0_9px_#6ee7b755]" : "bg-slate-500"}`}
      />
      {children}
    </span>
  );
}
export function Outcome({ forKey }: { forKey: string }) {
  const { results } = useWorkspace();
  const result = results[forKey];
  return result ? (
    <p
      role={result.error ? "alert" : "status"}
      className={`mt-3 break-words text-xs ${result.error ? "text-rose-300" : "text-slate-400"}`}
    >
      {result.text}
    </p>
  ) : null;
}
export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-8 text-center text-sm text-slate-500">{children}</p>;
}
export function QueryState({
  loading,
  error,
  updated,
}: {
  loading: boolean;
  error: string;
  updated?: number;
}) {
  if (error)
    return (
      <p
        role="alert"
        className="mb-4 rounded-xl bg-rose-400/10 p-3 text-sm text-rose-300"
      >
        {error}
        {updated ? " · 마지막 수신값을 표시합니다." : ""}
      </p>
    );
  return loading ? (
    <div
      role="status"
      aria-label="서버 상태 확인 중"
      className="mb-4 h-12 animate-pulse rounded-xl bg-white/5"
    />
  ) : null;
}
export function Progress({
  value,
  total,
  label,
}: {
  value?: number;
  total?: number;
  label: string;
}) {
  const ready = value !== undefined && total !== undefined && total > 0;
  return (
    <div
      className="h-2 overflow-hidden rounded-full bg-white/8"
      role={ready ? "progressbar" : undefined}
      aria-label={label}
      aria-valuenow={ready ? value : undefined}
      aria-valuemax={ready ? total : undefined}
      aria-valuemin={ready ? 0 : undefined}
    >
      <div
        className="h-full rounded-full bg-sky-400 transition-all duration-500"
        style={{
          width: ready
            ? `${Math.min(100, Math.max(0, (value / total) * 100))}%`
            : "0%",
        }}
      />
    </div>
  );
}
