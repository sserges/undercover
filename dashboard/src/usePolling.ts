import { useEffect, useState } from "react";

export interface Polled<T> {
  data: T | undefined;
  failed: boolean;
}

/** Load data now, then again every interval if one is given. */
export function usePolling<T>(
  load: () => Promise<T>,
  intervalMs?: number,
): Polled<T> {
  const [polled, setPolled] = useState<Polled<T>>({
    data: undefined,
    failed: false,
  });

  useEffect(() => {
    let active = true;
    const refresh = () => {
      load().then(
        (data) => {
          if (active) setPolled({ data, failed: false });
        },
        () => {
          if (active) setPolled((previous) => ({ ...previous, failed: true }));
        },
      );
    };
    refresh();
    const timer = intervalMs ? setInterval(refresh, intervalMs) : undefined;
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [load, intervalMs]);

  return polled;
}
