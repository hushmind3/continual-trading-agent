import { useEffect,useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Inbox, LoaderCircle, X } from "lucide-react";

export function Button({
  tone = "neutral",
  busy = false,
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: "neutral" | "primary" | "danger";
  busy?: boolean;
}) {
  return (
    <button
      type="button"
      {...props}
      disabled={props.disabled || busy}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition duration-150 active:scale-[.97] disabled:cursor-not-allowed disabled:opacity-45 ${tone === "primary" ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm shadow-blue-600/20" : tone === "danger" ? "bg-rose-50 text-rose-700 hover:bg-rose-100" : "bg-slate-100 text-slate-700 hover:bg-slate-200"} ${className}`}
    >
      {busy && <LoaderCircle size={15} className="animate-spin" />}
      {children}
    </button>
  );
}
export function Status({
  tone = "idle",
  inverted = false,
  children,
}: {
  tone?: string;
  inverted?: boolean;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium ${tone === "good" ? inverted ? "text-emerald-300" : "text-emerald-700" : tone === "bad" ? inverted ? "text-rose-300" : "text-rose-600" : tone === "warn" ? inverted ? "text-amber-300" : "text-amber-700" : "text-slate-400"}`}
    >
      <i
        className={`h-1.5 w-1.5 rounded-full ${tone === "good" ? "bg-emerald-500" : tone === "bad" ? "bg-rose-500" : tone === "warn" ? "bg-amber-500" : "bg-slate-300"}`}
      />
      {children}
    </span>
  );
}
export function Empty({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-32 flex-col items-center justify-center gap-3 px-5 py-7 text-center">
      <Inbox size={24} className="text-slate-300" />
      <div>
        <p className="text-sm font-medium text-slate-600">{title}</p>
        {detail && (
          <p className="mx-auto mt-1 max-w-lg text-xs leading-5 text-slate-400">
            {detail}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}
export function ErrorMessage({ message }: { message: string }) {
  return message ? (
    <div
      role="alert"
      className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700"
    >
      {message}
    </div>
  ) : null;
}
export function Skeleton() {
  return (
    <div aria-label="상태를 불러오는 중" className="space-y-5 animate-pulse">
      <div className="h-40 rounded-2xl bg-slate-200/60" />
      <div className="grid gap-5 md:grid-cols-2">
        <div className="h-64 rounded-2xl bg-slate-200/60" />
        <div className="h-64 rounded-2xl bg-slate-200/60" />
      </div>
    </div>
  );
}
export function Meter({
  value,
  label,
  detail,
  color = "bg-blue-500",
}: {
  value: number;
  label?: string;
  detail?: string;
  color?: string;
}) {
  return (
    <div>
      {label && (
        <div className="mb-2 flex justify-between gap-4 text-xs">
          <span className="font-medium text-slate-600">{label}</span>
          <span className="tabular-nums text-slate-400">{detail}</span>
        </div>
      )}
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-[width] duration-500 ${color}`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}
export function Drawer({
  title,
  open,
  onClose,
  children,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  const previous=useRef<HTMLElement|null>(null),wasOpen=useRef(false),panel=useRef<HTMLElement|null>(null);
  if(open&&!wasOpen.current)previous.current=document.activeElement as HTMLElement|null;
  wasOpen.current=open;
  useEffect(() => {
    if (!open) return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if(e.key==='Tab'){
        const controls=panel.current?.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled]),select:not([disabled]),summary,a[href],[tabindex="0"]');
        if(controls?.length){const first=controls[0],last=controls[controls.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
      }
    };
    window.addEventListener("keydown", key);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", key);
      document.body.style.overflow = "";
      previous.current?.focus();
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-end sm:items-stretch"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <button
        aria-label="닫기"
        className="absolute inset-0 z-0 bg-slate-950/30 backdrop-blur-sm"
        onClick={onClose}
      />
      <section ref={panel} className="relative z-10 max-h-[88dvh] w-full overflow-y-auto rounded-t-3xl bg-white p-6 shadow-2xl animate-[reveal_.2s_ease-out] sm:max-h-none sm:max-w-lg sm:rounded-none">
        <div className="mb-6 flex items-center justify-between gap-3">
          <h2 className="text-lg font-bold">{title}</h2>
          <Button
            autoFocus
            aria-label="닫기"
            onClick={onClose}
            className="px-2"
          >
            <X size={17} />
          </Button>
        </div>
        {children}
      </section>
    </div>
  );
}
export function Tabs({
  items,
  value,
  onChange,
}: {
  items: { id: string; label: string }[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="inline-flex rounded-xl bg-slate-100 p-1" role="tablist">
      {items.map((item) => (
        <button
          key={item.id}
          role="tab"
          aria-selected={value === item.id}
          onClick={() => onChange(item.id)}
          className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${value === item.id ? "bg-white text-slate-900 shadow-sm" : "text-slate-400 hover:text-slate-700"}`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
export function Sparkline({
  values,
  up = true,
  height = 48,
}: {
  values: number[];
  up?: boolean;
  height?: number;
}) {
  if (values.length < 2)
    return (
      <div
        className="flex items-center text-xs text-slate-400"
        style={{ height }}
      >
        두 번째 관측 대기
      </div>
    );
  const min = Math.min(...values),
    max = Math.max(...values),
    range = Math.max(max - min, 1e-9);
  const points = values
    .map(
      (v, i) =>
        `${(i / (values.length - 1)) * 200},${height - 4 - ((v - min) / range) * (height - 8)}`,
    )
    .join(" ");
  return (
    <svg
      viewBox={`0 0 200 ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      role="img"
      aria-label="실제 관측 추이"
    >
      <polyline
        fill="none"
        stroke={up ? "#f43f5e" : "#3b82f6"}
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
        points={points}
      />
    </svg>
  );
}
export const inputClass =
  "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-400 focus:ring-3 focus:ring-blue-100";
