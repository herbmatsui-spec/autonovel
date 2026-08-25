import { useEffect, useRef, useState, useCallback } from 'react';
import { connectTaskStream, type StreamConnectionState, type StreamError } from '../api';
import type { TaskStatus } from '../types';

export type { StreamConnectionState, StreamError };

interface UseTaskStreamCallbacks {
  onStatus: (status: TaskStatus) => void;
  onComplete: (status: TaskStatus) => void;
  onError: (error: StreamError) => void;
}

interface UseTaskStreamReturn {
  connectionState: StreamConnectionState;
  reconnect: () => void;
}

export function useTaskStream(
  taskId: string | null,
  callbacks: UseTaskStreamCallbacks
): UseTaskStreamReturn {
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const [connectionState, setConnectionState] = useState<StreamConnectionState>('closed');
  const disconnectRef = useRef<(() => void) | null>(null);
  const lastEventIdRef = useRef<string | undefined>(undefined);
  const taskIdRef = useRef(taskId);
  taskIdRef.current = taskId;

  const reconnect = useCallback(() => {
    if (disconnectRef.current) {
      disconnectRef.current();
      disconnectRef.current = null;
    }
    if (taskIdRef.current) {
      // Trigger reconnection by re-running the effect
      setConnectionState('connecting');
    }
  }, []);

  useEffect(() => {
    if (!taskId) {
      if (disconnectRef.current) {
        disconnectRef.current();
        disconnectRef.current = null;
      }
      setConnectionState('closed');
      return;
    }

    const cleanup = connectTaskStream({
      taskId,
      onUpdate: (status) => {
        // Track last event ID for potential resume (if server supports it)
        // This would need server-side support for Last-Event-ID
        callbacksRef.current.onStatus(status);
      },
      onComplete: (status) => {
        callbacksRef.current.onComplete(status);
        setConnectionState('closed');
        disconnectRef.current = null;
      },
      onError: (error) => {
        callbacksRef.current.onError(error);
        if (!error.recoverable) {
          setConnectionState('failed');
          disconnectRef.current = null;
        }
      },
      onStateChange: (state) => {
        setConnectionState(state);
      },
      onReconnecting: (attempt) => {
        // Could emit to callback if needed
        console.log(`Reconnecting attempt ${attempt}...`);
      },
      lastEventId: lastEventIdRef.current,
    });

    disconnectRef.current = cleanup;

    return () => {
      if (cleanup) {
        cleanup();
      }
      disconnectRef.current = null;
    };
  }, [taskId]);

  return { connectionState, reconnect };
}
