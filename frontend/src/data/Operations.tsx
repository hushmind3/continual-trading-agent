import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { request } from "./api";
import type { Control, Snapshot } from "./types";

interface Context {
  state: Snapshot | null;
  error: string;
  pending: Set<string>;
  refresh: () => Promise<void>;
  command: (name: Control, value: boolean) => Promise<void>;
}
const Operations = createContext<Context | null>(null);
export function OperationsProvider({ children }: { children: ReactNode }) {
  const sequence = useRef(0), applied = useRef(0);
  const [state, setState] = useState<Snapshot | null>(null),
    [error, setError] = useState(""),
    [pending, setPending] = useState(new Set<string>());
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    try {
      const next = await request<Snapshot>("state");
      if (!["finrlx-moe-ppo-v1","finrlx-unified-gpu-moe-v1"].includes(next.architecture))
        throw new Error("연결된 서버가 새 FinRL-X 운영 서버가 아닙니다.");
      if (current < applied.current) return;
      applied.current = current;
      setState(next);
      setError("");
    } catch (reason) {
      if (current < applied.current) return;
      applied.current = current;
      setError(
        reason instanceof Error ? reason.message : "서버 연결을 확인하세요.",
      );
    }
  }, []);
  useEffect(() => {
    let active = true;
    const tick = async () => {
      if (active) await refresh();
    };
    void tick();
    const timer = setInterval(() => void tick(), 2000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [refresh]);
  const command = async (name: Control, value: boolean) => {
    setPending((old) => new Set(old).add(name));
    try {
      await request(`controls/${name}`, { enabled: value });
      await refresh();
    } finally {
      setPending((old) => {
        const next = new Set(old);
        next.delete(name);
        return next;
      });
    }
  };
  return (
    <Operations.Provider
      value={{ state, error, pending, refresh, command }}
    >
      {children}
    </Operations.Provider>
  );
}
export function useOperations() {
  const value = useContext(Operations);
  if (!value) throw new Error("OperationsProvider가 필요합니다.");
  return value;
}
