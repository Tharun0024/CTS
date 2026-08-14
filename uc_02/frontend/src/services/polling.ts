import { useEffect, useRef, useCallback } from 'react';

/**
 * usePolling — polls `fetchFn` every `intervalMs` ms.
 * Stops automatically when `shouldStop(data)` returns true.
 *
 * Structure is designed so the real implementation can be swapped to
 * WebSocket/SSE without changing call sites in page components:
 *   - fetchFn  → WebSocket message handler
 *   - onData   → same callback
 *   - shouldStop → same predicate
 *
 * @param fetchFn   Async function that fetches the latest data
 * @param onData    Callback fired each time data arrives
 * @param shouldStop Predicate; return true to stop polling
 * @param intervalMs Poll interval (default: 5000ms)
 * @param enabled   Set to false to pause polling
 */
export function usePolling<T>(
  fetchFn: () => Promise<T>,
  onData: (data: T) => void,
  shouldStop: (data: T) => boolean,
  intervalMs = 5000,
  enabled = true
) {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stoppedRef = useRef(false);
  const onDataRef = useRef(onData);
  const shouldStopRef = useRef(shouldStop);
  const fetchFnRef = useRef(fetchFn);

  // Keep refs fresh without re-running the effect
  onDataRef.current = onData;
  shouldStopRef.current = shouldStop;
  fetchFnRef.current = fetchFn;

  const poll = useCallback(async () => {
    if (stoppedRef.current) return;
    try {
      const data = await fetchFnRef.current();
      onDataRef.current(data);
      if (shouldStopRef.current(data)) {
        stoppedRef.current = true;
        if (timerRef.current) clearInterval(timerRef.current);
      }
    } catch {
      // Silently swallow polling errors — page-level error handling covers initial load
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    stoppedRef.current = false;

    // Fire immediately, then on interval
    poll();
    timerRef.current = setInterval(poll, intervalMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [enabled, intervalMs, poll]);
}

// Terminal/actionable statuses — polling stops on these
export const TERMINAL_STATUSES = new Set([
  'ACCEPTED',
  'REJECTED',
  'MORE_INFO',
  'HUMAN_REVIEW',
  'RESUBMISSION_CHECK',
  'SUBMITTED_AGAIN',
  'DRAFT',
]);

export function isTerminalStatus(status: string): boolean {
  return TERMINAL_STATUSES.has(status);
}
