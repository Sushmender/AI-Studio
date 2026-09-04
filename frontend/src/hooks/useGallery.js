/**
 * useGallery.js — localStorage persistence for completed gallery items.
 *
 * Storage key: "ai_studio_gallery"
 * Format: JSON array of { id, created_at } objects (strings for legacy compat)
 *
 * On load: re-fetches each stored job result from backend.
 * Jobs that 404 (backend restarted) are silently dropped.
 *
 * created_at: unix timestamp (ms) stored at generation time for CDN expiry countdown.
 */
import { useState, useEffect, useCallback } from 'react';
import { getJobResult } from '../api/client';

const STORAGE_KEY = 'ai_studio_gallery';

// Each stored entry: { id: string, created_at: number }
function readStoredEntries() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    // Support legacy format: plain string IDs
    return parsed.map((entry) =>
      typeof entry === 'string' ? { id: entry, created_at: null } : entry,
    );
  } catch (_) {
    return [];
  }
}

function writeStoredEntries(entries) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch (_) {}
}

export function useGallery() {
  // Each item: { job_id, result_url, mode, raw_prompt, enhanced_prompt, latency_ms, created_at }
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load + refetch on mount
  useEffect(() => {
    const entries = readStoredEntries();
    if (entries.length === 0) {
      setLoading(false);
      return;
    }

    (async () => {
      const results = await Promise.allSettled(entries.map((e) => getJobResult(e.id)));
      const validItems = [];
      const validEntries = [];

      results.forEach((res, idx) => {
        if (res.status === 'fulfilled' && res.value && res.value.result_url) {
          validItems.push({
            ...res.value,
            job_id: entries[idx].id,
            created_at: entries[idx].created_at,
          });
          validEntries.push(entries[idx]);
        }
        // silently drop 404s and null results
      });

      // Persist only valid entries back to localStorage
      writeStoredEntries(validEntries);
      // Show newest first
      setItems(validItems.reverse());
      setLoading(false);
    })();
  }, []);

  /** Add a completed job result to the gallery. created_at should be a ms timestamp. */
  const addItem = useCallback((jobResult) => {
    if (!jobResult?.result_url) return;
    setItems((prev) => {
      // Avoid duplicates
      if (prev.some((i) => i.job_id === jobResult.job_id)) return prev;
      const next = [jobResult, ...prev];
      // Persist entries with created_at
      writeStoredEntries(
        next.map((i) => ({ id: i.job_id, created_at: i.created_at ?? null })),
      );
      return next;
    });
  }, []);

  /** Remove a specific item (e.g., user deletes from gallery). */
  const removeItem = useCallback((jobId) => {
    setItems((prev) => {
      const next = prev.filter((i) => i.job_id !== jobId);
      writeStoredEntries(next.map((i) => ({ id: i.job_id, created_at: i.created_at ?? null })));
      return next;
    });
  }, []);

  return { items, loading, addItem, removeItem };
}
