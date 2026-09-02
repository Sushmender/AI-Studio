/**
 * useToast.js — Lightweight custom toast notification hook.
 *
 * Usage:
 *   const { toasts, showToast, dismissToast } = useToast();
 *   showToast('✓ Image generated!', 'success');
 *   showToast('Something went wrong', 'error', 6000);
 */
import { useState, useCallback, useRef } from 'react';

let _nextId = 1;

/**
 * @typedef {{ id: number, message: string, type: 'success'|'error'|'info' }} Toast
 */

export function useToast() {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    clearTimeout(timers.current[id]);
    delete timers.current[id];
  }, []);

  /**
   * Show a toast.
   * @param {string} message
   * @param {'success'|'error'|'info'} type
   * @param {number} duration — ms before auto-dismiss (default 4000)
   */
  const showToast = useCallback(
    (message, type = 'success', duration = 4000) => {
      const id = _nextId++;
      setToasts((prev) => [...prev, { id, message, type }]);
      timers.current[id] = setTimeout(() => dismissToast(id), duration);
    },
    [dismissToast],
  );

  return { toasts, showToast, dismissToast };
}
