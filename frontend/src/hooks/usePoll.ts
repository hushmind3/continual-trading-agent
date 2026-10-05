import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../api/client";
export function usePoll<T>(path: string, interval = 4000) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState(0);
  const [failures, setFailures] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const flight = useRef<Promise<void> | null>(null);
  const refresh = useCallback(
    async (force = false) => {
      if (flight.current) {
        await flight.current;
        if (!force) return;
        if (flight.current) return flight.current;
      }
      const ac = new AbortController();
      controller.current = ac;
      const task = request<T>(path, undefined, ac.signal)
        .then((value) => {
          if (!ac.signal.aborted) {
            setData(value);
            setError("");
            setFailures(0);
            setUpdated(Date.now());
          }
        })
        .catch((e) => {
          if (!ac.signal.aborted) {
            setFailures((value) => value + 1);
            setError(e instanceof Error ? e.message : "서버 연결 실패");
          }
        })
        .finally(() => {
          if (flight.current === task) flight.current = null;
        });
      flight.current = task;
      return task;
    },
    [path],
  );
  useEffect(() => {
    let mounted = true;
    let timer: ReturnType<typeof setTimeout>;
    const run = async () => {
      await refresh();
      if (mounted) timer = setTimeout(run, interval);
    };
    void run();
    return () => {
      mounted = false;
      clearTimeout(timer);
      controller.current?.abort();
      flight.current = null;
    };
  }, [refresh, interval]);
  return { data, error, updated, failures, loading: !data && !error, refresh };
}
