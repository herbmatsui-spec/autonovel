import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getBooks,
  getBook,
  deleteBook,
  getPlots,
  getChapters,
  getTaskStatus,
  stopTask,
  checkBackendHealth,
  importChapter,
  runCommercialPipeline,
  refineErotic,
  approvePatch,
  rejectPatch,
  auditPlan,
  generateMarketing,
  getPendingPatches,
  generateEasy,
  planGeneration,
  expandPlots,
  rebuildPlots,
  critiqueOptimize,
  getIssues,
  resolveIssue,
  exportPackage,
} from '@/api';

const mockFetch = (data: any, ok = true, status = 200, text = 'OK') =>
  vi.fn(() =>
    Promise.resolve({
      ok,
      status,
      text: () => Promise.resolve(text),
      json: () => Promise.resolve(data),
    } as Response)
  );

describe('API client', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('getBooks should fetch and return books array', async () => {
    const mockBooks = [
      { id: 1, title: 'Test Book', genre: 'ファンタジー', concept: '', synopsis: '', target_eps: 10, created_at: '2024-01-01' },
    ];
    (globalThis as any).fetch = mockFetch(mockBooks);

    const result = await getBooks();
    expect(result).toEqual(mockBooks);
    expect((globalThis as any).fetch).toHaveBeenCalledTimes(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/books'),
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it('getBook should fetch single book by id', async () => {
    (globalThis as any).fetch = mockFetch({ id: 1, title: 'X' });
    await getBook(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/books/1'),
      expect.any(Object)
    );
  });

  it('deleteBook should send DELETE request', async () => {
    (globalThis as any).fetch = mockFetch({});
    await deleteBook(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/books/1'),
      expect.objectContaining({ method: 'DELETE' })
    );
  });

  it('getPlots should fetch plots for book', async () => {
    (globalThis as any).fetch = mockFetch([]);
    await getPlots(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/plots/1'),
      expect.any(Object)
    );
  });

  it('getChapters should fetch chapters for book', async () => {
    (globalThis as any).fetch = mockFetch([]);
    await getChapters(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/chapters/1'),
      expect.any(Object)
    );
  });

  it('getTaskStatus should fetch task status', async () => {
    const mockStatus = { task_id: 't1', is_running: true, current_step: 1, total_steps: 5, message: '' };
    (globalThis as any).fetch = mockFetch(mockStatus);
    const result = await getTaskStatus('t1');
    expect(result).toEqual(mockStatus);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/tasks/t1/status'),
      expect.any(Object)
    );
  });

  it('stopTask should POST to stop endpoint', async () => {
    (globalThis as any).fetch = mockFetch({});
    await stopTask('t1');
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/tasks/t1/stop'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('checkBackendHealth should fetch health endpoint', async () => {
    const mockHealth = { status: 'ok', database: 'ok', worker: 'ok', huey_backend: 'sqlite', queue_depth: 0 };
    (globalThis as any).fetch = mockFetch(mockHealth);
    const result = await checkBackendHealth();
    expect(result.status).toBe('ok');
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.any(Object)
    );
  });

  it('importChapter should POST to corrected episodes/chapters/import path', async () => {
    (globalThis as any).fetch = mockFetch({ task_id: 'imp1' });
    await importChapter({ book_id: 1, import_text: 'test' });
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/episodes/chapters/import'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('runCommercialPipeline should POST to /commercial/run', async () => {
    (globalThis as any).fetch = mockFetch({ task_id: 'com1' });
    await runCommercialPipeline({ book_id: 1 });
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/commercial/run'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('refineErotic should POST to /api/refine_erotic', async () => {
    (globalThis as any).fetch = mockFetch({ task_id: 'ref1' });
    await refineErotic({ book_id: 1, intensity: 2, platform_preset: 'kakuyomu_romance' });
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/refine_erotic'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('approvePatch should POST to approve endpoint', async () => {
    (globalThis as any).fetch = mockFetch({});
    await approvePatch(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/patches/1/approve'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('rejectPatch should POST to reject endpoint', async () => {
    (globalThis as any).fetch = mockFetch({});
    await rejectPatch(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/patches/1/reject'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('auditPlan should POST to plots/audit', async () => {
    (globalThis as any).fetch = mockFetch({});
    await auditPlan({ book_id: 1 });
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/plots/audit'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('generateMarketing should POST to marketing endpoint', async () => {
    (globalThis as any).fetch = mockFetch({ task_id: 'mkt1' });
    await generateMarketing({ book_id: 1 });
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/marketing/generate'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('getPendingPatches should fetch patches', async () => {
    (globalThis as any).fetch = mockFetch([]);
    await getPendingPatches(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/patches/1/pending'),
      expect.any(Object)
    );
  });

  it('background tasks (generateEasy, planGeneration, expandPlots, rebuildPlots, critiqueOptimize) should return task_id', async () => {
    (globalThis as any).fetch = mockFetch({ task_id: 'bg1' });
    expect(await generateEasy({ genre: 'test' })).toBe('bg1');
    expect(await planGeneration({ book_id: 1 })).toBe('bg1');
    expect(await expandPlots({ book_id: 1 })).toBe('bg1');
    expect(await rebuildPlots({ book_id: 1 })).toBe('bg1');
    expect(await critiqueOptimize({ book_id: 1 })).toBe('bg1');
  });

  it('getIssues should return issues array', async () => {
    (globalThis as any).fetch = mockFetch({ issues: [{ id: 1 }] });
    const result = await getIssues(1);
    expect(result).toEqual([{ id: 1 }]);
  });

  it('resolveIssue should POST to resolve endpoint', async () => {
    (globalThis as any).fetch = mockFetch({});
    await resolveIssue(1, 'ignore', 'key');
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/issues/1/resolve'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('should throw on HTTP error with message', async () => {
    (globalThis as any).fetch = mockFetch(null, false, 500, 'Server Error');
    await expect(getBooks()).rejects.toThrow('Server Error');
  });

  it('should throw on HTTP error without message body', async () => {
    (globalThis as any).fetch = mockFetch(null, false, 404, '');
    await expect(getBooks()).rejects.toThrow('HTTP 404');
  });
});
