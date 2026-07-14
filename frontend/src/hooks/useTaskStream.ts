import { useEffect, useRef } from 'react';
import { connectTaskStream } from '../api';
import type { TaskStatus } from '../types';

interface UseTaskStreamCallbacks {
  onStatus: (status: TaskStatus) => void;
  onComplete: (status: TaskStatus) => void;
  onError: (error: any) => void;
}

export function useTaskStream(
  taskId: string | null,
  callbacks: UseTaskStreamCallbacks
) {
  const disconnectRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (taskId) {
      const disconnect = connectTaskStream(
        taskId,
        callbacks.onStatus,
        callbacks.onComplete,
        callbacks.onError
      );
      disconnectRef.current = disconnect;
    }
    return () => {
      if (disconnectRef.current) {
        disconnectRef.current();
      }
    };
  }, [taskId, callbacks.onStatus, callbacks.onComplete, callbacks.onError]);
}
