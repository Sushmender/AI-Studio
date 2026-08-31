/**
 * useGallery.js — localStorage persistence for completed gallery items.
 *
 * Storage key: "ai_studio_gallery"
 * Format: JSON array of job IDs (strings)
 *
 * On load: re-fetches each stored job result from backend.
 * Jobs that 404 (backend restarted) are silently dropped.
 */
import { useState, useEffect, useCallback } from 'react';
import { getJobResult } from '../api/client';

const STORAGE_KEY = 'ai_studio_gallery';

function readStoredIds() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function writeStoredIds(ids) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch (_) {}
}

export function useGallery() {
  // Each item: { job_id, result_url, mode, raw_prompt, enhanced_prompt, latency_ms }
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load + refetch on mount
  useEffect(() => {
    const ids = readStoredIds();
    if (ids.length === 0) {
      setLoading(false);
      return;
    }

    (async () => {
      const results = await Promise.allSettled(ids.map((id) => getJobResult(id)));
      const validItems = [];
      const validIds = [];

      results.forEach((res, idx) => {
        if (res.status === 'fulfilled' && res.value && res.value.result_url) {
          validItems.push({ ...res.value, job_id: ids[idx] });
          validIds.push(ids[idx]);
        }
        // silently drop 404s and null results
      });

      // Persist only valid IDs back to localStorage
      writeStoredIds(validIds);
      // Show newest first
      setItems(validItems.reverse());
      setLoading(false);
    })();
  }, []);

  /** Add a completed job result to the gallery. */
  const addItem = useCallback((jobResult) => {
    if (!jobResult?.result_url) return;
    setItems((prev) => {
      // Avoid duplicates
      if (prev.some((i) => i.job_id === jobResult.job_id)) return prev;
      const next = [jobResult, ...prev];
      // Persist IDs
      writeStoredIds(next.map((i) => i.job_id));
      return next;
    });
  }, []);

  /** Remove a specific item (e.g., user deletes from gallery). */
  const removeItem = useCallback((jobId) => {
    setItems((prev) => {
      const next = prev.filter((i) => i.job_id !== jobId);
      writeStoredIds(next.map((i) => i.job_id));
      return next;
    });
  }, []);

  return { items, loading, addItem, removeItem };
}
