import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getBooks, deleteBook, checkBackendHealth } from '@/api';

describe('API client', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('getBooks should fetch and return books array', async () => {
    const mockBooks = [{ id: 1, title: 'Test Book', genre: 'ファンタジー', concept: '', synopsis: '', target_eps: 10, created_at: '2024-01-01' }];
    (globalThis as any).fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockBooks),
      } as Response)
    );

    const result = await getBooks();
    expect(result).toEqual(mockBooks);
    expect((globalThis as any).fetch).toHaveBeenCalledTimes(1);
  });

  it('deleteBook should send DELETE request', async () => {
    (globalThis as any).fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response)
    );

    await deleteBook(1);
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/books/1'),
      expect.objectContaining({ method: 'DELETE' })
    );
  });

  it('checkBackendHealth should fetch health endpoint', async () => {
    const mockHealth = { status: 'ok', database: 'ok', worker: 'ok', huey_backend: 'sqlite', queue_depth: 0 };
    (globalThis as any).fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockHealth),
      } as Response)
    );

    const result = await checkBackendHealth();
    expect(result.status).toBe('ok');
    expect((globalThis as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.any(Object)
    );
  });

  it('should throw on HTTP error', async () => {
    (globalThis as any).fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error'),
      } as Response)
    );

    await expect(getBooks()).rejects.toThrow('Internal Server Error');
  });
});
