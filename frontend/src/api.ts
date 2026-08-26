import type {
  Book,
  Plot,
  Chapter,
  Bible,
  OptimizationHistory,
  TaskStatus,
  EasyModeParams,
  EpisodeGenerateParams,
  EpisodeGenerateCandidatesParams,
  PlanGenerationParams,
  RetryFailedParams,
  PlotExpandParams,
  PlotRebuildParams,
  CritiqueOptimizeParams,
  AuditPlanParams,
  AuditPlanResult,
  ChapterImportParams,
  MarketingGenerateParams,
  PendingPatch,
  PromptVersion,
  NarrativeMetricTrend,
  PlanningOptions,
  StyleDnaResult,
  ExportPackageResult,
  Issue,
} from './types/api';

export type {
  Book,
  Plot,
  Chapter,
  Bible,
  OptimizationHistory,
  TaskStatus,
  EasyModeParams,
  EpisodeGenerateParams,
  EpisodeGenerateCandidatesParams,
  PlanGenerationParams,
  RetryFailedParams,
  PlotExpandParams,
  PlotRebuildParams,
  CritiqueOptimizeParams,
  AuditPlanParams,
  ChapterImportParams,
  MarketingGenerateParams,
  PendingPatch,
  PromptVersion,
  NarrativeMetricTrend,
  PlanningOptions,
  StyleDnaResult,
  ExportPackageResult,
  AuditPlanResult,
  Issue,
};

// useUserSettingsStore import removed, no config usage needed

// generic API request helper
async function apiRequest<T>(url: string, init?: RequestInit, apiKey?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> || {}),
  };
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  const res = await fetch(url, {
    credentials: 'include',
    headers,
    method: init?.method ?? 'GET',
    body: init?.body,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error: ${res.status} ${errorText}`);
  }

  const data: T = await res.json();
  return data;
}

// helper to add X-API-Key header
export function withAuth(init: RequestInit, apiKey: string): RequestInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> || {}),
    'X-API-Key': apiKey,
  };
  return {
    ...init,
    headers,
  };
}

// safely access import.meta.env for Vite environment variables
const VITE_API_URL = (import.meta as unknown as { env?: { VITE_API_URL?: string } })?.env?.VITE_API_URL;
const API_BASE_URL = VITE_API_URL || '/api';
const API_BASE_URL_NO_API = API_BASE_URL.replace('/api', '');


// REST GET/DELETE helper functions
export async function getBooks(): Promise<Book[]> {
  return apiRequest(`${API_BASE_URL}/books`);
}

export async function getBook(bookId: number): Promise<Book> {
  return apiRequest(`${API_BASE_URL}/books/${bookId}`);
}

export async function deleteBook(bookId: number): Promise<void> {
  return apiRequest(`${API_BASE_URL}/books/${bookId}`, { method: 'DELETE' });
}

export async function getPlots(bookId: number): Promise<Plot[]> {
  return apiRequest(`${API_BASE_URL}/plots/${bookId}`);
}

export async function getChapters(bookId: number): Promise<Chapter[]> {
  return apiRequest(`${API_BASE_URL}/chapters/${bookId}`);
}

export async function getBible(bookId: number): Promise<Bible> {
  return apiRequest(`${API_BASE_URL}/bibles/${bookId}`);
}

export async function getOptHistory(bookId: number): Promise<OptimizationHistory[]> {
  return apiRequest(`${API_BASE_URL}/optimization_history/${bookId}`);
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  return apiRequest(`${API_BASE_URL}/tasks/${taskId}/status`);
}

export async function stopTask(taskId: string): Promise<void> {
  return apiRequest(`${API_BASE_URL}/tasks/${taskId}/stop`, { method: 'POST' });
}

export async function getPlanningOptions(): Promise<PlanningOptions> {
  return apiRequest(`${API_BASE_URL}/config/planning_options`);
}

export type StreamConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'closed' | 'failed';

export interface StreamError {
  type: 'network' | 'server' | 'parse' | 'aborted';
  message: string;
  recoverable: boolean;
  originalError: unknown;
}

export interface ConnectTaskStreamOptions {
  taskId: string;
  onUpdate: (status: TaskStatus) => void;
  onComplete: (status: TaskStatus) => void;
  onError: (error: StreamError) => void;
  onStateChange?: (state: StreamConnectionState) => void;
  onReconnecting?: (attempt: number) => void;
  lastEventId?: string;
}

function classifyError(error: unknown, readyState: number): StreamError {
  if (readyState === EventSource.CLOSED) {
    return {
      type: 'network',
      message: '接続が切断されました。再接続を試みます...',
      recoverable: true,
      originalError: error,
    };
  }
  if (error instanceof SyntaxError || error instanceof TypeError) {
    return {
      type: 'parse',
      message: 'サーバーからのデータ形式が不正です。',
      recoverable: true,
      originalError: error,
    };
  }
  return {
    type: 'server',
    message: 'サーバーエラーが発生しました。',
    recoverable: true,
    originalError: error,
  };
}

export function connectTaskStream(
  options: ConnectTaskStreamOptions
): () => void {
  const {
    taskId,
    onUpdate,
    onComplete,
    onError,
    onStateChange,
    onReconnecting,
    lastEventId,
  } = options;

  let eventSource: EventSource | null = null;
  let manuallyClosed = false;
  let reconnectAttempt = 0;
  const MAX_RECONNECT_ATTEMPTS = 10;
  const BASE_RECONNECT_DELAY_MS = 1000;
  const MAX_RECONNECT_DELAY_MS = 30000;

  const updateState = (state: StreamConnectionState) => {
    onStateChange?.(state);
  };

  const attemptConnect = (customLastEventId?: string) => {
    if (manuallyClosed) return;

    updateState('connecting');

    const sseUrl = `${API_BASE_URL}/tasks/${taskId}/stream`;
    const url = customLastEventId ? `${sseUrl}?last_event_id=${encodeURIComponent(customLastEventId)}` : sseUrl;

    eventSource = new EventSource(url);

    eventSource.onopen = () => {
      reconnectAttempt = 0;
      updateState('connected');
    };

    eventSource.onmessage = (event) => {
      try {
        const status: TaskStatus = JSON.parse(event.data);
        onUpdate(status);
        if (!status.is_running) {
          manuallyClosed = true;
          updateState('closed');
          onComplete(status);
          eventSource?.close();
          eventSource = null;
        }
      } catch (e) {
        const streamError = classifyError(e, eventSource?.readyState ?? EventSource.CLOSED);
        streamError.type = 'parse';
        onError(streamError);
        eventSource?.close();
        eventSource = null;
        scheduleReconnect(event.lastEventId || customLastEventId);
      }
    };

    eventSource.onerror = (error) => {
      if (manuallyClosed) return;

      const readyState = eventSource?.readyState ?? EventSource.CLOSED;
      const streamError = classifyError(error, readyState);

      if (readyState === EventSource.CLOSED && !manuallyClosed) {
        // Unexpected closure - attempt reconnect
        updateState('reconnecting');
        scheduleReconnect(eventSource?.url ? extractLastEventId(eventSource.url) : customLastEventId);
      } else {
        // Other errors (CONNECTING -> failed)
        updateState('failed');
        onError(streamError);
        eventSource?.close();
        eventSource = null;
      }
    };
  };

  const extractLastEventId = (url: string): string | undefined => {
    const match = url.match(/[?&]last_event_id=([^&]+)/);
    return match ? decodeURIComponent(match[1]) : undefined;
  };

  const scheduleReconnect = (lastEventId?: string) => {
    if (manuallyClosed) return;
    if (reconnectAttempt >= MAX_RECONNECT_ATTEMPTS) {
      updateState('failed');
      onError({
        type: 'network',
        message: '最大再接続回数に達しました。手動で再試行してください。',
        recoverable: false,
        originalError: new Error('Max reconnect attempts reached'),
      });
      return;
    }

    const delay = Math.min(
      BASE_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempt) + Math.random() * 1000,
      MAX_RECONNECT_DELAY_MS
    );
    reconnectAttempt += 1;
    onReconnecting?.(reconnectAttempt);

    setTimeout(() => {
      if (!manuallyClosed) {
        attemptConnect(lastEventId);
      }
    }, delay);
  };

  // Initial connection
  attemptConnect(lastEventId);

  return () => {
    manuallyClosed = true;
    eventSource?.close();
    eventSource = null;
  };
}


// Background task triggering endpoints (POST)
async function triggerTask(endpoint: string, body: unknown, apiKey?: string): Promise<string> {
  const data = await apiRequest<{ task_id: string }>(`${API_BASE_URL}${endpoint}`, withAuth({
    method: 'POST',
    body: JSON.stringify(body),
  }, apiKey ?? ''));
  return data.task_id;
}

export async function generateEasy(params: EasyModeParams, apiKey?: string): Promise<string> {
  return triggerTask('/easy_mode/generate', params, apiKey);
}

export async function planGeneration(params: PlanGenerationParams, apiKey?: string): Promise<string> {
  return triggerTask('/plots/plan_generation', params, apiKey);
}

export async function generateEpisodes(params: EpisodeGenerateParams, apiKey?: string): Promise<string> {
  return triggerTask('/episodes/generate', params, apiKey);
}

export async function generateEpisodesCandidates(params: EpisodeGenerateCandidatesParams, apiKey?: string): Promise<string> {
  return triggerTask('/episodes/generate', { ...params, mode: 'candidates' }, apiKey);
}

export async function retryFailedEpisodes(params: RetryFailedParams, apiKey?: string): Promise<string> {
  return triggerTask('/episodes/retry_failed', params, apiKey);
}

export async function expandPlots(params: PlotExpandParams, apiKey?: string): Promise<string> {
  return triggerTask('/plots/expand', params, apiKey);
}

export async function expandPlotsCandidates(params: PlotExpandParams, apiKey?: string): Promise<string> {
  return triggerTask('/plots/expand', { ...params, mode: 'candidates' }, apiKey);
}

export async function rebuildPlots(params: PlotRebuildParams, apiKey?: string): Promise<string> {
  return triggerTask('/plots/rebuild', params, apiKey);
}

export async function critiqueOptimize(params: CritiqueOptimizeParams, apiKey?: string): Promise<string> {
  return triggerTask('/critique/optimize', params, apiKey);
}

// Synchronous operations (Direct Response)
export async function auditPlan(params: AuditPlanParams, apiKey?: string): Promise<AuditPlanResult> {
  return apiRequest(`${API_BASE_URL}/plots/audit`, withAuth({
    method: 'POST',
    body: JSON.stringify(params),
  }, apiKey ?? ''));
}

export async function importChapter(params: ChapterImportParams, apiKey?: string): Promise<string> {
  return triggerTask('/episodes/chapters/import', params, apiKey);
}

export async function generateMarketing(params: MarketingGenerateParams, apiKey?: string): Promise<string> {
  return triggerTask('/marketing/generate', params, apiKey);
}

export type CommercialPipelineParams = {
  book_id: number;
  config?: Record<string, unknown>;
  samples?: unknown[];
  platforms?: string[];
};

export async function runCommercialPipeline(params: CommercialPipelineParams, apiKey?: string): Promise<Record<string, unknown>> {
  return apiRequest(`${API_BASE_URL_NO_API}/commercial/run`, withAuth({
    method: 'POST',
    body: JSON.stringify(params),
  }, apiKey ?? ''));
}

export function getExportPackageUrl(bookId: number): string {
  return `${API_BASE_URL}/marketing/export_package/${bookId}`;
}

// Pending patches API
export async function getPendingPatches(bookId: number): Promise<PendingPatch[]> {
  return apiRequest(`${API_BASE_URL}/patches/${bookId}/pending`);
}

export async function approvePatch(patchId: number): Promise<void> {
  return apiRequest(`${API_BASE_URL}/patches/${patchId}/approve`, {
    method: 'POST',
  });
}

export async function rejectPatch(patchId: number): Promise<void> {
  return apiRequest(`${API_BASE_URL}/patches/${patchId}/reject`, {
    method: 'POST',
  });
}

export async function editPatch(patchId: number, content: string): Promise<void> {
  return apiRequest(`${API_BASE_URL}/patches/${patchId}/edit`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

// Prompt versions API
export async function getPromptVersions(bookId: number): Promise<PromptVersion[]> {
  return apiRequest(`${API_BASE_URL}/prompt_versions/${bookId}`);
}

export async function rollbackPromptVersion(bookId: number, versionId: number, reason: string): Promise<void> {
  return apiRequest(`${API_BASE_URL}/prompt_versions/${bookId}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ version_id: versionId, reason }),
  });
}

export async function getNarrativeMetricsTrend(book_id: number, branch_id: number): Promise<NarrativeMetricTrend[]> {
  return apiRequest(`${API_BASE_URL}/narrative_metrics/${book_id}/${branch_id}`);
}

interface HealthCheckResponse {
  status?: string;
  database?: string;
  worker?: string;
  huey_backend?: string;
  queue_depth?: number;
  checks?: {
    database?: { status?: string };
    worker?: { status?: string };
    [key: string]: unknown;
  };
}

// Health check
export async function checkBackendHealth(): Promise<{
  status: string;
  database: string;
  worker: string;
  huey_backend: string;
  queue_depth: number;
}> {
  const data = await apiRequest<HealthCheckResponse>(`${API_BASE_URL_NO_API}/health`);
  const checks = data?.checks || {};
  const dbStatus = checks?.database?.status || data?.database || 'offline';
  const workerStatus = checks?.worker?.status || data?.worker || 'offline';
  
  // If database is ok, consider API server healthy enough for the UI to proceed
  const isHealthy = data?.status === 'ok' || dbStatus === 'ok';

  return {
    status: isHealthy ? 'ok' : (data?.status || 'error'),
    database: dbStatus,
    worker: workerStatus,
    huey_backend: data?.huey_backend || 'unknown',
    queue_depth: data?.queue_depth ?? 0,
  };
}

export async function analyzeStyleDna(sample: string): Promise<StyleDnaResult> {
  return apiRequest(`${API_BASE_URL}/marketing/analyze_style_dna`, {
    method: 'POST',
    body: JSON.stringify({ sample }),
  });
}

export async function getIssues(bookId: number): Promise<Issue[]> {
  const data = await apiRequest<{ issues?: Issue[] }>(`${API_BASE_URL}/issues/books/${bookId}`);
  return data?.issues ?? [];
}

export async function resolveIssue(issueId: number, action: string): Promise<void> {
  return apiRequest(`${API_BASE_URL}/issues/${issueId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

export async function exportPackage(bookId: number): Promise<ExportPackageResult> {
  return apiRequest(`${API_BASE_URL}/marketing/export_package/${bookId}`, {
    method: 'POST',
  });
}

export type RefineEroticParams = {
  book_id: number;
  intensity: number;
  platform_preset: string;
};

export async function refineErotic(params: RefineEroticParams, apiKey?: string): Promise<string> {
  return triggerTask('/refine_erotic', params, apiKey);
}
