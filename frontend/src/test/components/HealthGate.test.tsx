import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { HealthGate } from '@/components/HealthGate';

vi.mock('@/api', () => ({
  checkBackendHealth: vi.fn(),
}));

import { checkBackendHealth } from '@/api';

describe('HealthGate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (checkBackendHealth as any).mockImplementation(() => new Promise(() => {}));
    render(
      <HealthGate>
        <div data-testid="child">Content</div>
      </HealthGate>
    );
    expect(screen.getByText('システムを初期化中...')).toBeDefined();
  });

  it('renders children when backend is healthy', async () => {
    (checkBackendHealth as any).mockResolvedValue({
      status: 'ok',
      database: 'ok',
      worker: 'ok',
      huey_backend: 'sqlite',
      queue_depth: 0,
    });
    render(
      <HealthGate>
        <div data-testid="child">Protected Content</div>
      </HealthGate>
    );
    await waitFor(() => {
      expect(screen.getByTestId('child').textContent).toBe('Protected Content');
    });
  });

  it('renders error state when backend is unreachable', async () => {
    (checkBackendHealth as any).mockRejectedValue(new Error('Connection refused'));
    render(
      <HealthGate>
        <div>Should not appear</div>
      </HealthGate>
    );
    await waitFor(() => {
      expect(screen.getByText(/バックエンドサーバーに接続できません/)).toBeDefined();
    });
  });
});
