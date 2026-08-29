/**
 * frontend/src/lib/sseClient.ts - Server-Sent Events (SSE) リアルタイム接続クライアント
 */

export interface AgentStatusEvent {
  agent: string;
  phase: string;
  message: string;
  iteration?: number;
  ep_num?: number;
  score?: number;
  is_approved?: boolean;
  issues_count?: number;
  char_length?: number;
  requires_revision?: boolean;
  total_issues?: number;
}

export interface PipelineProgressEvent {
  phase: string;
  progress: number;
  message: string;
  current_ep?: number;
}

export type SSEEventCallback = (eventType: string, data: unknown) => void;

class SSEClient {
  private eventSource: EventSource | null = null;
  private listeners: Set<SSEEventCallback> = new Set();
  private isConnecting: boolean = false;
  private reconnectTimeout: number | null = null;

  public connect(apiKey?: string): void {
    if (this.eventSource || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    const url = new URL('/api/v1/events/stream', window.location.origin);
    if (apiKey) {
      url.searchParams.set('api_key', apiKey);
    }

    try {
      this.eventSource = new EventSource(url.toString());

      this.eventSource.onopen = () => {
        this.isConnecting = false;
        console.log('[SSE] Connection established.');
        this.notify('connection_status', { status: 'connected' });
      };

      // 共通メッセージハンドラ
      this.eventSource.addEventListener('agent_status', (e: MessageEvent) => {
        try {
          const parsed = JSON.parse(e.data);
          this.notify('agent_status', parsed.data || parsed);
        } catch (err) {
          console.error('[SSE] Failed to parse agent_status:', err);
        }
      });

      this.eventSource.addEventListener('pipeline_progress', (e: MessageEvent) => {
        try {
          const parsed = JSON.parse(e.data);
          this.notify('pipeline_progress', parsed.data || parsed);
        } catch (err) {
          console.error('[SSE] Failed to parse pipeline_progress:', err);
        }
      });

      this.eventSource.addEventListener('axis_locks', (e: MessageEvent) => {
        try {
          const parsed = JSON.parse(e.data);
          this.notify('axis_locks', parsed.data || parsed);
        } catch (err) {
          console.error('[SSE] Failed to parse axis_locks:', err);
        }
      });

      this.eventSource.addEventListener('connected', (e: MessageEvent) => {
        console.log('[SSE] Stream handshake confirmed:', e.data);
      });

      this.eventSource.onerror = (err) => {
        console.warn('[SSE] Connection error. Reconnecting...', err);
        this.notify('connection_status', { status: 'reconnecting' });
        this.disconnect();
        this.scheduleReconnect(apiKey);
      };
    } catch (e) {
      this.isConnecting = false;
      console.error('[SSE] Failed to create EventSource:', e);
      this.scheduleReconnect(apiKey);
    }
  }

  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnecting = false;
    if (this.reconnectTimeout !== null) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  public subscribe(callback: SSEEventCallback): () => void {
    this.listeners.add(callback);
    return () => {
      this.listeners.delete(callback);
    };
  }

  private notify(eventType: string, data: unknown): void {
    this.listeners.forEach((listener) => {
      try {
        listener(eventType, data);
      } catch (err) {
        console.error('[SSE] Listener execution error:', err);
      }
    });
  }

  private scheduleReconnect(apiKey?: string): void {
    if (this.reconnectTimeout !== null) return;
    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect(apiKey);
    }, 3000);
  }
}

export const sseClient = new SSEClient();
