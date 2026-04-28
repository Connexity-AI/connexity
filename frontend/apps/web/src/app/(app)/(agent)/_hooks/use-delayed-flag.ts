import { useEffect, useRef, useState } from 'react';

/**
 * Returns `true` while `flag` is true, and stays true for an extra
 * `delay` ms after `flag` goes false — useful for keeping spinners
 * visible long enough to be perceived.
 */
export function useDelayedFlag(flag: boolean, delay = 300): boolean {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (flag) {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      setVisible(true);
      return;
    }
    timerRef.current = setTimeout(() => {
      setVisible(false);
      timerRef.current = null;
    }, delay);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [flag, delay]);

  return visible;
}
