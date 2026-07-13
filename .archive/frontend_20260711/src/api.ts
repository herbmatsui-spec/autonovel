import type {
  Book,
  Plot,
  Chapter,
  Bible,
  OptimizationHistory,
  TaskStatus,
  EasyModeParams,
  EpisodeGenerateParams,
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
};

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// REST GET/DELETE helper functions
export async function getBooks(): Promise<Book[]> {
  const response = await fetch(`${API_BASE_URL}/books`);
  if (!response.ok) {
    throw new Error('Failed to fetch books');
  }
  return response.json();
}

export async function getBook(bookId: number): Promise<Book> {
  const response = await fetch(`${API_BASE_URL}/books/${bookId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch book detail');
  }
  return response.json();
}

export async function deleteBook(bookId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/books/${bookId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete book');
  }
}

export async function getPlots(bookId: number): Promise<Plot[]> {
  const response = await fetch(`${API_BASE_URL}/plots/${bookId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch plots');
  }
  return response.json();
}

export async function getChapters(bookId: number): Promise<Chapter[]> {
  const response = await fetch(`${API_BASE_URL}/chapters/${bookId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch chapters');
  }
  return response.json();
}

export async function getBible(bookId: number): Promise<Bible> {
  const response = await fetch(`${API_BASE_URL}/bibles/${bookId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch bible settings');
  }
  return response.json();
}

export async function getOptHistory(bookId: number): Promise<OptimizationHistory[]> {
  const response = await fetch(`${API_BASE_URL}/optimization_history/${bookId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch optimization history');
  }
  return response.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/status`);
  if (!response.ok) {
    throw new Error('Failed to fetch task status');
  }
  return response.json();
}

export async function stopTask(taskId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/stop`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to stop task');
  }
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
async function triggerTask(endpoint: string, body: any): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Failed on POST ${endpoint}`);
  }
  const data = await response.json();
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

export async function retryFailedEpisodes(params: RetryFailedParams): Promise<string> {
  return triggerTask('/episodes/retry_failed', params);
}

export async function expandPlots(params: PlotExpandParams): Promise<string> {
  return triggerTask('/plots/expand', params);
}

export async function rebuildPlots(params: PlotRebuildParams): Promise<string> {
  return triggerTask('/plots/rebuild', params);
}

export async function critiqueOptimize(params: CritiqueOptimizeParams): Promise<string> {
  return triggerTask('/critique/optimize', params);
}

// Synchronous operations (Direct Response)
export async function auditPlan(params: AuditPlanParams): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/plots/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new Error('Failed to audit plan');
  }
  return response.json();
}

export async function importChapter(params: ChapterImportParams): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/chapters/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new Error('Failed to import chapter');
  }
  return response.json();
}

export async function generateMarketing(params: MarketingGenerateParams): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/marketing/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new Error('Failed to generate marketing pack');
  }
  return response.json();
}

export function getExportPackageUrl(bookId: number, apiKey: string): string {
  return `${API_BASE_URL}/marketing/export_package/${bookId}?api_key=${encodeURIComponent(apiKey)}`;
}

// Pending patches API
export async function getPendingPatches(bookId: number): Promise<PendingPatch[]> {
  const response = await fetch(`${API_BASE_URL}/patches/${bookId}/pending`);
  if (!response.ok) throw new Error('Failed to fetch pending patches');
  return response.json();
}

export async function approvePatch(patchId: number): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/patches/${patchId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Failed to approve patch');
  }
  return response.json();
}

export async function rejectPatch(patchId: number): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/patches/${patchId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error('Failed to reject patch');
  return response.json();
}

export async function editPatch(patchId: number, content: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/patches/${patchId}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Failed to edit patch');
  }
  return response.json();
}

// Prompt versions API
export async function getPromptVersions(bookId: number): Promise<PromptVersion[]> {
  const response = await fetch(`${API_BASE_URL}/prompt_versions/${bookId}`);
  if (!response.ok) throw new Error('Failed to fetch prompt versions');
  return response.json();
}

export async function rollbackPromptVersion(bookId: number, versionId: number, reason: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/prompt_versions/${bookId}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version_id: versionId, reason }),
  });
  if (!response.ok) throw new Error('Failed to rollback prompt version');
  return response.json();
}

export async function getNarrativeMetricsTrend(book_id: number, branch_id: number): Promise<NarrativeMetricTrend[]> {
  const response = await fetch(`${API_BASE_URL}/narrative_metrics/${book_id}/${branch_id}`);
  if (!response.ok) {
    throw new Error('Failed to fetch narrative metrics trend');
  }
  return response.json();
}

