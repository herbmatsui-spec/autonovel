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
  ChapterImportParams,
  MarketingGenerateParams,
  PromptVersion,
  NarrativeMetricTrend,
  PlanningOptions,
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
};

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

async function apiRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

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

export function connectTaskStream(
  taskId: string,
  onUpdate: (status: TaskStatus) => void,
  onComplete: (status: TaskStatus) => void,
  onError: (error: any) => void
): () => void {
  const sseUrl = `${API_BASE_URL}/tasks/${taskId}/stream`;
  const eventSource = new EventSource(sseUrl);

  eventSource.onmessage = (event) => {
    try {
      const status: TaskStatus = JSON.parse(event.data);
      onUpdate(status);
      if (!status.is_running) {
        onComplete(status);
        eventSource.close();
      }
    } catch (e) {
      onError(e);
      eventSource.close();
    }
  };

  eventSource.onerror = (error) => {
    onError(error);
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}


// Background task triggering endpoints (POST)
async function triggerTask(endpoint: string, body: unknown): Promise<string> {
  const data = await apiRequest<{ task_id: string }>(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return data.task_id;
}

export async function generateEasy(params: EasyModeParams): Promise<string> {
  return triggerTask('/easy_mode/generate', params);
}

export async function planGeneration(params: PlanGenerationParams): Promise<string> {
  return triggerTask('/plots/plan_generation', params);
}

export async function generateEpisodes(params: EpisodeGenerateParams): Promise<string> {
  return triggerTask('/episodes/generate', params);
}

export async function generateEpisodesCandidates(params: EpisodeGenerateCandidatesParams): Promise<string> {
  return triggerTask('/episodes/generate', { ...params, mode: 'candidates' });
}

export async function retryFailedEpisodes(params: RetryFailedParams): Promise<string> {
  return triggerTask('/episodes/retry_failed', params);
}

export async function expandPlots(params: PlotExpandParams): Promise<string> {
  return triggerTask('/plots/expand', params);
}

export async function expandPlotsCandidates(params: PlotExpandParams): Promise<string> {
  return triggerTask('/plots/expand', { ...params, mode: 'candidates' });
}

export async function rebuildPlots(params: PlotRebuildParams): Promise<string> {
  return triggerTask('/plots/rebuild', params);
}

export async function critiqueOptimize(params: CritiqueOptimizeParams): Promise<string> {
  return triggerTask('/critique/optimize', params);
}

// Synchronous operations (Direct Response)
export async function auditPlan(params: AuditPlanParams): Promise<any> {
  return apiRequest(`${API_BASE_URL}/plots/audit`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function importChapter(params: ChapterImportParams): Promise<any> {
  return apiRequest(`${API_BASE_URL}/episodes/chapters/import`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function generateMarketing(params: MarketingGenerateParams): Promise<any> {
  return apiRequest(`${API_BASE_URL}/marketing/generate`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export type CommercialPipelineParams = {
  book_id: number;
  config?: Record<string, any>;
  samples?: any[];
  platforms?: string[];
};

export async function runCommercialPipeline(params: CommercialPipelineParams): Promise<any> {
  return apiRequest(`${API_BASE_URL.replace('/api', '')}/commercial/run`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export function getExportPackageUrl(bookId: number, apiKey: string): string {
  return `${API_BASE_URL}/marketing/export_package/${bookId}?api_key=${encodeURIComponent(apiKey)}`;
}

// Pending patches API
export async function getPendingPatches(bookId: number): Promise<PendingPatch[]> {
  return apiRequest(`${API_BASE_URL}/patches/${bookId}/pending`);
}

export async function approvePatch(patchId: number): Promise<any> {
  return apiRequest(`${API_BASE_URL}/patches/${patchId}/approve`, {
    method: 'POST',
  });
}

export async function rejectPatch(patchId: number): Promise<any> {
  return apiRequest(`${API_BASE_URL}/patches/${patchId}/reject`, {
    method: 'POST',
  });
}

export async function editPatch(patchId: number, content: string): Promise<any> {
  return apiRequest(`${API_BASE_URL}/patches/${patchId}/edit`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

// Prompt versions API
export async function getPromptVersions(bookId: number): Promise<PromptVersion[]> {
  return apiRequest(`${API_BASE_URL}/prompt_versions/${bookId}`);
}

export async function rollbackPromptVersion(bookId: number, versionId: number, reason: string): Promise<any> {
  return apiRequest(`${API_BASE_URL}/prompt_versions/${bookId}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ version_id: versionId, reason }),
  });
}

export async function getNarrativeMetricsTrend(book_id: number, branch_id: number): Promise<NarrativeMetricTrend[]> {
  return apiRequest(`${API_BASE_URL}/narrative_metrics/${book_id}/${branch_id}`);
}

// Health check
export async function checkBackendHealth(): Promise<{
  status: string;
  database: string;
  worker: string;
  huey_backend: string;
  queue_depth: number;
}> {
  const baseUrl = API_BASE_URL.replace('/api', '');
  return apiRequest(`${baseUrl}/health`);
}

export async function analyzeStyleDna(sample: string): Promise<any> {
  return apiRequest(`${API_BASE_URL}/marketing/analyze_style_dna`, {
    method: 'POST',
    body: JSON.stringify({ sample }),
  });
}

export async function getIssues(bookId: number): Promise<any[]> {
  const data = await apiRequest<{ issues?: any[] }>(`${API_BASE_URL}/issues/books/${bookId}`);
  return data?.issues ?? [];
}

export async function resolveIssue(issueId: number, action: string, apiKey: string): Promise<any> {
  return apiRequest(`${API_BASE_URL}/issues/${issueId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ action, api_key: apiKey }),
  });
}

export async function exportPackage(bookId: number, apiKey: string): Promise<any> {
  return apiRequest(`${API_BASE_URL}/marketing/export_package/${bookId}`, {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export type RefineEroticParams = {
  book_id: number;
  intensity: number;
  platform_preset: string;
};

export async function refineErotic(params: RefineEroticParams): Promise<any> {
  return apiRequest(`${API_BASE_URL}/refine_erotic`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
