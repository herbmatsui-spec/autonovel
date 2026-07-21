import { useEffect, useRef } from 'react';
import { connectTaskStream } from '../api';
import type { TaskStatus } from '../types';

interface UseTaskStreamCallbacks {
  onStatus: (status: TaskStatus) => void;
  onComplete: (status: TaskStatus) => void;
  onError: (error: any) => void;
}

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

export function useTaskStream(
  taskId: string | null,
  callbacks: UseTaskStreamCallbacks
) {
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const retryCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const disconnectRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const attemptConnect = () => {
      if (disconnectRef.current) {
        disconnectRef.current();
      }
      const cleanup = connectTaskStream(
        taskId,
        (status) => callbacksRef.current.onStatus(status),
        (status) => {
          retryCountRef.current = 0;
          callbacksRef.current.onComplete(status);
        },
        (error) => {
          if (retryCountRef.current < MAX_RETRIES) {
            const delay = BASE_DELAY_MS * Math.pow(2, retryCountRef.current);
            retryCountRef.current += 1;
            reconnectTimerRef.current = setTimeout(attemptConnect, delay);
          } else {
            callbacksRef.current.onError(error);
          }
        }
      );
      disconnectRef.current = cleanup;
    };

    attemptConnect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (disconnectRef.current) {
        disconnectRef.current();
      }
    };
  }, [taskId]);
}
