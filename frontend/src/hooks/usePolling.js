import { useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 2000; // plan.md: HTTP-polling раз в 2 секунды, без WebSocket

/**
 * Polls `fetchFn` every 2s. Keeps the last good result on the screen while a
 * request is in flight (no flicker), and surfaces `loading` only for the
 * very first fetch — a stale-while-revalidate pattern appropriate for the
 * two-browser sync checkpoint in plan.md.
 */
export function usePolling(fetchFn, deps = [], { enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setLoading(true);

    async function tick() {
      try {
        const result = await fetchFnRef.current();
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    tick();
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  return { data, error, loading };
}
