import { useEffect, useState } from "react";

/**
 * Debounces a rapidly changing value.
 *
 * Search fires an upstream request per keystroke otherwise, which wastes the
 * TVMaze rate limit budget for no user benefit.
 */
export function useDebounce<T>(value: T, delayMs = 350): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
