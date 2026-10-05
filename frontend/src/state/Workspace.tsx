import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePoll } from "../hooks/usePoll";
import { request } from "../api/client";
import type {
  Assembly,
  Model,
  Provider,
  Registry,
  SystemStatus,
} from "../api/types";
import { destinations, modelDefinitions, pageIndex } from "../config";
import { stateLabel } from "../format";
export interface Event {
  id: number;
  time: string;
  text: string;
  error?: boolean;
}
function useWorkspaceState() {
  const status = usePoll<SystemStatus>("/api/status", 3000);
  const moe = usePoll<Model>("/api/trading-moe/status", 3000);
  const assembly = usePoll<Assembly>("/api/assembly/status", 5000);
  const registry = usePoll<Registry>("/api/experts", 10000);
  const provider = usePoll<Provider>("/api/provider", 15000);
  const [menu, setMenu] = useState(false);
  const [notice, setNoticeState] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [readId, setReadId] = useState(0);
  const sequence = useRef(0);
  const noticeRef = useRef(false);
  function setNotice(value: boolean) {
    noticeRef.current = value;
    setNoticeState(value);
    if (value) setReadId(sequence.current);
  }
  const [page, setPageState] = useState(() => pageIndex(location.hash.slice(1)));
  const [filter, setFilter] = useState("전체");
  const [events, setEvents] = useState<Event[]>([]);
  const [pending, setPending] = useState<Record<string, boolean>>({});
  const locks = useRef(new Set<string>());
  const last = useRef<Record<string, string>>({});
  const expectedStops = useRef(new Set<string>());
  const expectedReconnectUntil = useRef(0);
  const [results, setResults] = useState<
    Record<string, { text: string; error: boolean }>
  >({});
  const push = useCallback((text: string, error = false) => {
    const id = ++sequence.current;
    setEvents((v) =>
      [{ id, time: new Date().toISOString(), text, error }, ...v].slice(0, 50),
    );
    if (noticeRef.current) setReadId(id);
  }, []);
  const setPage = useCallback((index: number) => {
    location.hash = destinations[index].hash;
    setMenu(false);
  }, []);
  useEffect(() => {
    const hash = () => {
      setPageState(pageIndex(location.hash.slice(1)));
      setSelected(null);
    };
    window.addEventListener("hashchange", hash);
    return () => window.removeEventListener("hashchange", hash);
  }, []);
  const command = useCallback(
    async (path: string, body: unknown = {}, label = "요청", key = path) => {
      if (locks.current.has(key)) return false;
      locks.current.add(key);
      setPending((v) => ({ ...v, [key]: true }));
      setResults((v) => ({ ...v, [key]: { text: "요청 중", error: false } }));
      const stopping =
        path === "/api/stop"
          ? ["champion", "candidate"]
          : path.endsWith("/stop") &&
              ["champion", "candidate", "trading-moe"].includes(key)
            ? [key]
            : path === "/api/assembly/trial/stop"
              ? ["candidate"]
              : [];
      stopping.forEach((role) => expectedStops.current.add(role));
      if (path === "/api/server/restart")
        expectedReconnectUntil.current = Date.now() + 30000;
      const queries = path.startsWith("/api/trading-moe/")
        ? [moe]
        : path.startsWith("/api/assembly/")
          ? [assembly, status]
          : path.startsWith("/api/provider/")
            ? [provider, status]
            : [status];
      try {
        const response = await request<{ assembly?: Assembly }>(path, body);
        if (response.assembly) {
          last.current.promotions = String(response.assembly.promotions ?? 0);
          last.current.rejections = String(response.assembly.rejections ?? 0);
        }
        await Promise.all(queries.map((query) => query.refresh(true)));
        setResults((v) => ({
          ...v,
          [key]: { text: `${label} 요청 처리됨`, error: false },
        }));
        return true;
      } catch (e) {
        const text = e instanceof Error ? e.message : "요청 실패";
        stopping.forEach((role) => expectedStops.current.delete(role));
        setResults((v) => ({ ...v, [key]: { text, error: true } }));
        return false;
      } finally {
        locks.current.delete(key);
        setPending((v) => ({ ...v, [key]: false }));
      }
    },
    [status.refresh, moe.refresh, assembly.refresh, provider.refresh],
  );
  const connected = !!status.data && !status.error;
  const models = modelDefinitions.map((d) => {
    const query = d.role === "trading-moe" ? moe : status;
    const native =
      (d.role === "trading-moe"
        ? moe.data
        : status.data?.model_runtime?.[d.role]) ?? {};
    const data: Model = {
      ...native,
      loaded:
        native.loaded ??
        (native.alive === true && (native.load_count ?? 0) > 0),
      decision:
        native.decision ??
        status.data?.decisions?.find((entry) => entry.role === d.role),
    };
    const available = !!query.data && !query.error && !!data.status;
    const running =
      available && data.status === "running" && data.alive !== false;
    const enabled =
      data.alive === true ||
      data.requested === true ||
      ["running", "loading", "starting", "saving", "stopping"].includes(
        data.status ?? "",
      );
    const displayStatus = !available
      ? query.error
        ? "연결 끊김"
        : "상태 확인 중"
      : data.status === "running" && data.alive === false
        ? "중지됨"
        : stateLabel(data.status);
    return {
      ...d,
      data,
      available,
      running,
      displayStatus,
      enabled,
      busy: !!pending[d.role],
    };
  });
  const toggleModel = (name: string) => {
    const m = models.find((x) => x.name === name);
    if (!m || !m.available) return;
    const path =
      m.role === "trading-moe" ? "/api/trading-moe" : `/api/models/${m.role}`;
    void command(
      `${path}/${m.enabled ? "stop" : "start"}`,
      {},
      `${m.name} ${m.enabled ? "저장 후 정지" : "시작"}`,
      m.role,
    );
  };
  const setFeed = (enabled: boolean) => {
    if (connected)
      void command(
        enabled ? "/api/start" : "/api/stop",
        enabled
          ? {
              mode: status.data?.mode ?? "live",
              horizon: status.data?.horizon ?? "1m",
            }
          : {},
        enabled ? "시장 데이터 시작" : "시세·Champion·Candidate 정지",
        "feed",
      );
  };
  const setPaper = (enabled: boolean) => {
    if (connected)
      void command(
        "/api/modes",
        { paper_enabled: enabled },
        `가상체결 ${enabled ? "허용" : "중지"}`,
        "modes",
      );
  };
  const setLearn = (enabled: boolean) => {
    if (connected)
      void command(
        "/api/modes",
        { learning_enabled: enabled },
        `학습 ${enabled ? "허용" : "중지"}`,
        "modes",
      );
  };
  const setObserve = (enabled: boolean) => {
    if (connected)
      void command(
        "/api/modes",
        { observe_enabled: enabled },
        `판단 ${enabled ? "허용" : "중지"}`,
        "modes",
      );
  };
  useEffect(() => {
    for (const definition of modelDefinitions) {
      const data =
        definition.role === "trading-moe"
          ? moe.data
          : status.data?.model_runtime?.[definition.role];
      if (!data) continue;
      const previous = last.current[definition.role];
      const errorKey = `${definition.role}:error`;
      const intentional =
        data.stop_requested===true || data.requested===false ||
        expectedStops.current.has(definition.role) ||
        locks.current.has(definition.role) ||
        locks.current.has("feed") ||
        locks.current.has("assembly");
      if (previous !== undefined && !intentional) {
        if (data.error && data.error !== last.current[errorKey])
          push(`${definition.name}: ${data.error}`, true);
        else if (
          ["running", "loading", "starting"].includes(previous) &&
          ["stopped", "error"].includes(data.status ?? "")
        )
          push(`${definition.name} 실행이 예상치 않게 중단되었습니다.`, true);
      }
      last.current[definition.role] = data.status ?? "";
      last.current[errorKey] = data.error ?? "";
      if (data.status === "stopped" || data.status === "error")
        expectedStops.current.delete(definition.role);
    }
    const connectionError = status.error || moe.error;
    if (
      connectionError &&
      Math.max(status.failures, moe.failures) >= 2 &&
      Date.now() > expectedReconnectUntil.current &&
      last.current.connection === "connected"
    )
      push("서버 상태를 받을 수 없습니다. 연결을 확인해 주세요.", true);
    if (
      connectionError &&
      Math.max(status.failures, moe.failures) >= 2 &&
      Date.now() > expectedReconnectUntil.current
    )
      last.current.connection = "disconnected";
    else if (status.data && moe.data) last.current.connection = "connected";
    if (assembly.data) {
      for (const [key, title] of [
        ["promotions", "Candidate 승격"],
        ["rejections", "Candidate 평가 탈락"],
      ] as const) {
        const count = String(assembly.data[key] ?? 0);
        const previous = last.current[key];
        if (
          previous !== undefined &&
          Number(count) > Number(previous) &&
          !locks.current.has("assembly")
        )
          push(title);
        last.current[key] = count;
      }
    }
  }, [
    status.data,
    status.error,
    status.failures,
    moe.data,
    moe.error,
    moe.failures,
    assembly.data,
    push,
  ]);
  return {
    status,
    moe,
    assembly,
    registry,
    provider,
    menu,
    setMenu,
    notice,
    setNotice,
    unread: events.some((event) => event.id > readId),
    selected,
    setSelected,
    page,
    setPage,
    filter,
    setFilter,
    events,
    pending,
    results,
    command,
    models,
    toggleModel,
    connected,
    feed: connected && !!status.data?.feed_running,
    setFeed,
    paper: connected && !!status.data?.paper_enabled,
    setPaper,
    learn: connected && !!status.data?.learning_enabled,
    setLearn,
    observe: connected && !!status.data?.observe_enabled,
    setObserve,
  };
}
export type WorkspaceState = ReturnType<typeof useWorkspaceState>;
export type RuntimeModel = WorkspaceState["models"][number];
const Context = createContext<WorkspaceState | null>(null);
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const value = useWorkspaceState();
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useWorkspace() {
  const value = useContext(Context);
  if (!value) throw new Error("WorkspaceProvider required");
  return value;
}
