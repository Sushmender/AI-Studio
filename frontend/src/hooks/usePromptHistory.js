/**
 * usePromptHistory.js — localStorage persistence for the last 10 submitted prompts.
 *
 * Storage key: "ai_studio_prompt_history"
 * Format: JSON object { image: string[], video: string[] }
 *   — Each array is most-recent-first, capped at MAX_HISTORY entries.
 *
 * Unlike useGallery (which stores job IDs and refetches), prompt history stores
 * the prompt strings directly — no backend roundtrip needed.
 */
import { useState, useCallback } from 'react';

const STORAGE_KEY = 'ai_studio_prompt_history';
const MAX_HISTORY = 10;

function readHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { image: [], video: [] };
    const parsed = JSON.parse(raw);
    return {
      image: Array.isArray(parsed?.image) ? parsed.image : [],
      video: Array.isArray(parsed?.video) ? parsed.video : [],
    };
  } catch (_) {
    return { image: [], video: [] };
  }
}

function writeHistory(history) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch (_) {}
}

export function usePromptHistory() {
  const [history, setHistory] = useState(() => readHistory());

  /**
   * Add a prompt string to the history for a given mode.
   * Deduplicates (moves existing entry to top), trims to MAX_HISTORY.
   * @param {string} prompt
   * @param {'image'|'video'} mode
   */
  const addToHistory = useCallback((prompt, mode) => {
    if (!prompt?.trim()) return;
    const trimmed = prompt.trim();
    setHistory((prev) => {
      const existing = prev[mode] ?? [];
      // Remove duplicate, then prepend
      const deduped = existing.filter((p) => p !== trimmed);
      const next = [trimmed, ...deduped].slice(0, MAX_HISTORY);
      const updated = { ...prev, [mode]: next };
      writeHistory(updated);
      return updated;
    });
  }, []);

  /**
   * Clear history for a given mode (or both if mode is omitted).
   * @param {'image'|'video'|undefined} mode
   */
  const clearHistory = useCallback((mode) => {
    setHistory((prev) => {
      const updated = mode
        ? { ...prev, [mode]: [] }
        : { image: [], video: [] };
      writeHistory(updated);
      return updated;
    });
  }, []);

  return { history, addToHistory, clearHistory };
}
