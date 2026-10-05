import { useState } from "react";
import { useWorkspace } from "../state/Workspace";
import { request } from "../api/client";
import { Action, Outcome, QueryState } from "../components/controls";
import { date } from "../format";
export function ConnectionPage() {
  const { provider, command, pending } = useWorkspace();
  const [environment, setEnvironment] = useState("real");
  const [appKey, setAppKey] = useState("");
  const [secret, setSecret] = useState("");
  const [account, setAccount] = useState("");
  const [ip, setIp] = useState("");
  const [ipPending, setIpPending] = useState(false);
  const data = provider.data;
  const busy = !!pending.provider;
  async function save(connect: boolean) {
    const ok = await command(
      `/api/provider/${connect ? "connect" : "save"}`,
      { provider: "kiwoom", environment, app_key: appKey, secret, account },
      connect ? "인증 저장 후 연결 확인" : "인증 저장",
      "provider",
    );
    if (ok) {
      setAppKey("");
      setSecret("");
      setAccount("");
    }
  }
  async function publicIp() {
    setIpPending(true);
    try {
      const result = await request<{ ip: string }>("/api/provider/public-ip");
      setIp(result.ip);
    } catch (error) {
      setIp(error instanceof Error ? error.message : "IP 확인 실패");
    } finally {
      setIpPending(false);
    }
  }
  const inputClass =
    "w-full rounded-lg bg-white/5 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-sky-400";
  return (
    <div className="max-w-2xl">
      <QueryState {...provider} />
      <section className="mb-8 border-b border-white/10 pb-6">
        <h2 className="text-lg font-semibold">
          {data?.provider_name ?? "증권사 연결"}
        </h2>
        <p className="mt-3 text-sm text-slate-400">
          {data?.saved ? "인증 정보 저장됨" : "저장된 인증 정보 없음"} ·{" "}
          {data?.environment === "real"
            ? "실서버"
            : data?.environment === "paper"
              ? "모의 서버"
              : "서버 정보 미수신"}
        </p>
        {data?.last_test && (
          <p
            className={`mt-3 text-xs ${data.last_test.ok ? "text-teal-300" : "text-rose-300"}`}
          >
            마지막 연결 확인 · {date(data.last_test.time)} ·{" "}
            {data.last_test.message}
          </p>
        )}
        <div className="mt-5 flex flex-wrap gap-3">
          <Action
            disabled={!data || busy}
            onClick={() =>
              void command(
                "/api/provider/test",
                { provider: data?.provider, environment: data?.environment },
                "저장된 인증 연결 확인",
                "provider",
              )
            }
          >
            연결 확인
          </Action>
          <Action disabled={ipPending} onClick={() => void publicIp()}>
            {ipPending ? "확인 중" : "공인 IP 확인"}
          </Action>
          {data?.saved && (
            <Action
              disabled={busy}
              onClick={() => {
                if (window.confirm("저장된 인증 정보를 지우시겠습니까?"))
                  void command(
                    "/api/provider/clear",
                    { provider: data.provider },
                    "인증 정보 지우기",
                    "provider",
                  );
              }}
            >
              인증 지우기
            </Action>
          )}
        </div>
        {ip && <p className="mt-4 text-xs text-slate-400">{ip}</p>}
      </section>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save(true);
        }}
        className="space-y-5"
      >
        <h2 className="text-sm font-semibold">인증 정보 변경</h2>
        <label className="block text-xs text-slate-400">
          서버
          <select
            value={environment}
            onChange={(event) => setEnvironment(event.target.value)}
            className={`mt-2 ${inputClass}`}
          >
            <option value="real">실서버 · 주문 허용과 별개</option>
            <option value="paper">모의 서버</option>
          </select>
        </label>
        {[
          { label: "앱 키", value: appKey, set: setAppKey, type: "password" },
          {
            label: "앱 시크릿",
            value: secret,
            set: setSecret,
            type: "password",
          },
          { label: "계좌번호", value: account, set: setAccount, type: "text" },
        ].map((field) => (
          <label key={field.label} className="block text-xs text-slate-400">
            {field.label}
            <input
              required
              type={field.type}
              autoComplete="off"
              value={field.value}
              onChange={(event) => field.set(event.target.value)}
              className={`mt-2 ${inputClass}`}
            />
          </label>
        ))}
        <div className="flex flex-wrap gap-3">
          <Action
            type="submit"
            primary
            disabled={busy || !appKey || !secret || !account}
          >
            저장 후 연결 확인
          </Action>
          <Action
            type="button"
            disabled={busy || !appKey || !secret || !account}
            onClick={() => void save(false)}
          >
            저장만
          </Action>
        </div>
      </form>
      <Outcome forKey="provider" />
    </div>
  );
}
