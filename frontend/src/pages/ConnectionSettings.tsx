import { useEffect, useState } from "react";
import { KeyRound, Link2, Save, ShieldCheck } from "lucide-react";
import { request } from "../data/api";
import { useOperations } from "../data/Operations";
import type { OpsSettings } from "../data/types";
import {
  Button,
  ErrorMessage,
  Skeleton,
  Status,
  Tabs,
  inputClass,
} from "../ui/Primitives";
import { ControlButton } from "../ui/ControlButton";
import { date, percent } from "../ui/format";

export function ConnectionSettings() {
  const { state, refresh } = useOperations();
  const [environment, setEnvironment] = useState("real"),
    [key, setKey] = useState(""),
    [secret, setSecret] = useState(""),
    [error, setError] = useState(""),
    [feedback, setFeedback] = useState(""),
    [busy, setBusy] = useState(""),
    [settings, setSettings] = useState<OpsSettings | null>(null);
  useEffect(() => {
    if (state && !settings) {
      setSettings(state.settings);
      setEnvironment(state.provider.environment);
    }
  }, [state, settings]);
  if (!state || !settings) return <Skeleton />;
  const act = async (name: string, body: unknown) => {
    setBusy(name);
    setError("");
    setFeedback("");
    try {
      const response = await request<{ ok?: boolean; message?: string }>(
        name,
        body,
      );
      if (response.ok === false)
        throw new Error(response.message ?? "연결 확인 실패");
      setKey("");
      setSecret("");
      setFeedback(
        name === "settings"
          ? "설정을 적용했습니다."
          : "연결 상태를 확인했습니다.",
      );
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "요청 실패");
    } finally {
      setBusy("");
    }
  };
  const running =
    state.controls.engine ||
    ["agent", "learner", "experts"].some((k) => state.workers[k]?.alive);
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[1fr_1fr]">
      <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200/50">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <Link2 size={18} className="text-blue-500" />
            키움 시세 연결
          </h2>
          <Status tone={state.provider.saved ? "good" : "idle"}>
            {state.provider.saved ? "인증 저장됨" : "미설정"}
          </Status>
        </div>
        <div className="space-y-5">
          <Tabs
            items={[
              { id: "real", label: "실전 시세" },
              { id: "paper", label: "모의 시세" },
            ]}
            value={environment}
            onChange={setEnvironment}
          />
          <label className="block text-xs font-medium text-slate-500">
            App Key
            <input
              autoComplete="off"
              className={`${inputClass} mt-2`}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder={
                state.provider.has_app_key
                  ? "새 키로 변경할 때만 입력"
                  : "App Key"
              }
            />
          </label>
          <label className="block text-xs font-medium text-slate-500">
            Secret Key
            <input
              autoComplete="new-password"
              type="password"
              className={`${inputClass} mt-2`}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder={
                state.provider.has_secret
                  ? "보안 저장소에 보관됨"
                  : "Secret Key"
              }
            />
          </label>
          <p className="flex items-center gap-2 text-xs text-slate-400">
            <ShieldCheck size={14} />
            운영체제 보안 저장소에 보관 · 시세 인증만 사용
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              tone="primary"
              busy={busy === "provider/connect"}
              onClick={() =>
                void act("provider/connect", {
                  environment,
                  app_key: key,
                  secret,
                })
              }
            >
              <KeyRound size={14} />
              저장 · 연결 확인
            </Button>
            <Button
              busy={busy === "provider/test"}
              disabled={!state.provider.saved}
              onClick={() => void act("provider/test", {})}
            >
              저장된 연결 테스트
            </Button>
          </div>
          {state.provider.last_test && (
            <p className="text-xs text-slate-400">
              마지막 확인 {date(state.provider.last_test.time)} ·{" "}
              {state.provider.last_test.ok ? "연결 성공" : "연결 실패"}
            </p>
          )}
          {state.provider.vault_error && (
            <ErrorMessage message={state.provider.vault_error} />
          )}
        </div>
      </section>
      <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200/50">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-bold">운영 기준</h2>
          {running && <ControlButton name="engine" label="MoE" compact />}
        </div>
        <div className="space-y-4">
          <label className="block text-xs font-medium text-slate-500">
            MoE 파일
            <input
              className={`${inputClass} mt-2`}
              disabled={running}
              value={settings.expert_checkpoint}
              onChange={(e) =>
                setSettings({ ...settings, expert_checkpoint: e.target.value })
              }
            />
          </label>
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="종목 최대 비중"
              value={settings.risk.max_asset_weight * 100}
              suffix="%"
              disabled={running}
              change={(v) =>
                setSettings({
                  ...settings,
                  risk: { ...settings.risk, max_asset_weight: v / 100 },
                })
              }
            />
            <Field
              label="전체 최대 투자"
              value={settings.risk.max_exposure * 100}
              suffix="%"
              disabled={running}
              change={(v) =>
                setSettings({
                  ...settings,
                  risk: { ...settings.risk, max_exposure: v / 100 },
                })
              }
            />
            <Field
              label="최대 손실폭"
              value={settings.risk.max_drawdown * 100}
              suffix="%"
              disabled={running}
              change={(v) =>
                setSettings({
                  ...settings,
                  risk: { ...settings.risk, max_drawdown: v / 100 },
                })
              }
            />
            <Field
              label="학습 배치"
              value={settings.learning.batch_size}
              suffix="개"
              disabled={running}
              change={(v) =>
                setSettings({
                  ...settings,
                  learning: { ...settings.learning, batch_size: v },
                })
              }
            />
          </div>
          <details className="border-t border-slate-100 pt-4">
            <summary className="cursor-pointer text-xs font-semibold text-slate-500">
              학습 · 자원 설정
            </summary>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <Field
                label="학습률"
                value={settings.learning.learning_rate}
                step="0.0001"
                disabled={running}
                change={(v) =>
                  setSettings({
                    ...settings,
                    learning: { ...settings.learning, learning_rate: v },
                  })
                }
              />
              <Field
                label="CPU 학습 threads"
                value={settings.learning.cpu_threads}
                disabled={running}
                change={(v) =>
                  setSettings({
                    ...settings,
                    learning: { ...settings.learning, cpu_threads: v },
                  })
                }
              />
              <Field
                label="RAM 여유"
                value={settings.resources.ram_reserve_gib}
                suffix="GiB"
                disabled={running}
                change={(v) =>
                  setSettings({
                    ...settings,
                    resources: { ...settings.resources, ram_reserve_gib: v },
                  })
                }
              />
              <Field
                label="VRAM 여유"
                value={settings.resources.vram_reserve_gib}
                suffix="GiB"
                disabled={running}
                step="0.5"
                change={(v) =>
                  setSettings({
                    ...settings,
                    resources: { ...settings.resources, vram_reserve_gib: v },
                  })
                }
              />
            </div>
          </details>
          <Button
            tone="primary"
            busy={busy === "settings"}
            disabled={running}
            onClick={() => void act("settings", settings)}
          >
            <Save size={14} />
            기준 적용
          </Button>
          {running && (
            <p className="text-xs text-slate-400">
              MoE가 완전히 정지한 뒤 기준을 변경할 수 있습니다.
            </p>
          )}
          <p className="text-xs text-slate-400">
            체결 비용 {percent(settings.risk.fee)} · 가격 미끄러짐{" "}
            {percent(settings.risk.slippage, 2)}
          </p>
        </div>
      </section>
      {error && <ErrorMessage message={error} />}{" "}
      {feedback && (
        <p role="status" className="text-sm text-emerald-700">
          {feedback}
        </p>
      )}
    </div>
  );
}
function Field({
  label,
  value,
  change,
  suffix = "",
  step = "1",
  disabled = false,
}: {
  label: string;
  value: number;
  change: (v: number) => void;
  suffix?: string;
  step?: string;
  disabled?: boolean;
}) {
  return (
    <label className="block text-xs font-medium text-slate-500">
      {label} {suffix && <span className="text-slate-300">{suffix}</span>}
      <input
        type="number"
        step={step}
        disabled={disabled}
        value={value}
        onChange={(e) => change(Number(e.target.value))}
        className={`${inputClass} mt-2 tabular-nums`}
      />
    </label>
  );
}
