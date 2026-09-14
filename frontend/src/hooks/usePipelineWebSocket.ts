import { useState, useEffect, useCallback, useRef } from 'react';

export interface PipelineEvent {
  event_type: string;
  book_id: number;
  task_id: string;
  timestamp: string;
  payload: Record<string, any>;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

export interface PipelineState {
  status: ConnectionStatus;
  latestEvent: PipelineEvent | null;
  tasks: Record<string, { state: string; progress: number; payload: any }>;
  scoreData: {
    initialScore?: number;
    currentScore?: number;
    delta?: number;
    specialists?: Record<string, number>;
  };
  actionableDiffs: Array<{ dimension: string; directive: string; timestamp: string }>;
}

export function usePipelineWebSocket(bookId: number | null) {
  const [state, setState] = useState<PipelineState>({
    status: 'disconnected',
    latestEvent: null,
    tasks: {},
    scoreData: {},
    actionableDiffs: [],
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!bookId) return;

    setState(prev => ({ ...prev, status: 'connecting' }));
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    const token = localStorage.getItem('AUTONOVEL_API_KEY') || '';
    const tokenParam = token ? `?token=${encodeURIComponent(token)}` : '';
    const wsUrl = `${protocol}//${host}/api/ws/pipeline/${bookId}${tokenParam}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setState(prev => ({ ...prev, status: 'connected' }));
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data: PipelineEvent = JSON.parse(event.data);
        if (data.event_type === 'ping') {
          ws.send('ping');
          return;
        }

        setState(prev => {
          const nextTasks = { ...prev.tasks };
          const nextScoreData = { ...prev.scoreData };
          const nextDiffs = [...prev.actionableDiffs];

          if (data.event_type === 'task_started' || data.event_type === 'task_updated') {
            nextTasks[data.task_id] = {
              state: data.payload.state || 'running',
              progress: data.payload.progress || 0,
              payload: data.payload,
            };
          } else if (data.event_type === 'score_updated' || data.event_type === 'pdca_cycle') {
            if (data.payload.initial_score !== undefined) nextScoreData.initialScore = data.payload.initial_score;
            if (data.payload.final_score !== undefined || data.payload.score !== undefined) {
              nextScoreData.currentScore = data.payload.final_score ?? data.payload.score;
            }
            if (data.payload.score_delta !== undefined) nextScoreData.delta = data.payload.score_delta;
            if (data.payload.scores_by_specialist) nextScoreData.specialists = data.payload.scores_by_specialist;
          } else if (data.event_type === 'audit_diff' || data.payload.actionable_diffs) {
            const diffs = data.payload.actionable_diffs || [data.payload];
            diffs.forEach((d: any) => {
              if (d.directive || d.message) {
                nextDiffs.unshift({
                  dimension: d.dimension || 'general',
                  directive: d.directive || d.message,
                  timestamp: data.timestamp,
                });
              }
            });
          }

          return {
            ...prev,
            latestEvent: data,
            tasks: nextTasks,
            scoreData: nextScoreData,
            actionableDiffs: nextDiffs.slice(0, 50), // Keep latest 50
          };
        });
      } catch (err) {
        console.error('Failed to parse WebSocket pipeline event:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('Pipeline WebSocket error:', error);
    };

    ws.onclose = () => {
      setState(prev => ({ ...prev, status: 'disconnected' }));
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current += 1;
        setState(prev => ({ ...prev, status: 'reconnecting' }));
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
        setTimeout(connect, delay);
      }
    };
  }, [bookId]);

  useEffect(() => {
    if (!bookId) return;
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [bookId, connect]);

  return state;
}
