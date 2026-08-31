/**
 * useJobPolling.js — Polls /jobs/{id}/status on an adaptive interval.
 *
 * Adaptive intervals:
 *   image → 2 000 ms
 *   video → 5 000 ms
 *
 * Stops polling automatically when status is "done" or "failed".
 *
 * Returns:
 *   { status, result, error, elapsedMs, estimatedWait }
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { getJobStatus, getJobResult, mapJobErrorType, ApiError } from '../api/client';

const INTERVALS = { image: 2000, video: 5000 };

export function useJobPolling(jobId, mode = 'image') {
  const [status, setStatus] = useState(null);         // queued | generating | done | failed
  const [result, setResult] = useState(null);          // { result_url, mode, ... }
  const [error, setError] = useState(null);            // { errorType, message, provider }
  const [elapsedMs, setElapsedMs] = useState(0);
  const [estimatedWait, setEstimatedWait] = useState(null);

  const startTimeRef = useRef(null);
  const intervalRef = useRef(null);
  const isTerminalRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    if (!jobId || isTerminalRef.current) return;

    // Elapsed time
    if (startTimeRef.current) {
      setElapsedMs(Date.now() - startTimeRef.current);
    }

    try {
      const statusData = await getJobStatus(jobId);
      setStatus(statusData.status);

      if (statusData.estimated_wait_seconds && !estimatedWait) {
        setEstimatedWait(statusData.estimated_wait_seconds * 1000);
      }

      if (statusData.status === 'done') {
        isTerminalRef.current = true;
        stopPolling();
        // Fetch full result
        try {
          const resultData = await getJobResult(jobId);
          setResult(resultData);
        } catch (_) {
          // Status is done but result fetch failed — surface partial info
          setResult({ result_url: null, mode: statusData.mode });
        }
      } else if (statusData.status === 'failed') {
        isTerminalRef.current = true;
        stopPolling();
        const { errorType, message } = mapJobErrorType(statusData.error_type, mode);
        setError({
          errorType,
          message: statusData.error || message,
          provider: statusData.provider || '',
        });
      }
    } catch (err) {
      if (err instanceof ApiError) {
        // Don't stop polling on transient network errors — just note the error
        if (err.errorType === 'network_offline') {
          setError({ errorType: 'network_offline', message: err.userMessage, provider: '' });
        }
      }
    }
  }, [jobId, mode, estimatedWait, stopPolling]);

  useEffect(() => {
    if (!jobId) return;

    // Reset all state for a fresh job
    setStatus('queued');
    setResult(null);
    setError(null);
    setElapsedMs(0);
    setEstimatedWait(null);
    isTerminalRef.current = false;
    startTimeRef.current = Date.now();

    // Immediate first poll
    poll();

    const interval = INTERVALS[mode] ?? 2000;
    intervalRef.current = setInterval(poll, interval);

    return () => stopPolling();
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  return { status, result, error, elapsedMs, estimatedWait };
}
