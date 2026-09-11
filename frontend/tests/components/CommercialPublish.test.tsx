import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PlatformBadge } from '../../src/components/common/PlatformBadge';
import { PublicationScheduleTable } from '../../src/components/commercial/PublicationScheduleTable';
import { PublicationScheduleModal } from '../../src/components/commercial/PublicationScheduleModal';
import { PublicationErrorModal } from '../../src/components/commercial/PublicationErrorModal';
import { CommercialPublishPanel } from '../../src/components/commercial/CommercialPublishPanel';
import * as commercialApi from '../../src/api/commercial';
import '@testing-library/jest-dom';

// Mock API
vi.mock('../../src/api/commercial', () => ({
  getPublicationSchedules: vi.fn(),
  createPublicationSchedule: vi.fn(),
  cancelPublicationSchedule: vi.fn(),
  runPublicationScheduleNow: vi.fn(),
}));

const mockSchedules = [
  {
    id: 1,
    platform: 'narou' as const,
    episode_range: [1, 5] as [number, number],
    scheduled_at: '2026-10-01T10:00:00Z',
    status: 'pending' as const,
    error_message: null,
    book_id: 123,
    created_at: '2026-09-01T10:00:00Z',
  },
  {
    id: 2,
    platform: 'kakuyomu' as const,
    episode_range: [6, 10] as [number, number],
    scheduled_at: '2026-10-02T10:00:00Z',
    status: 'failed' as const,
    error_message: 'API Connection Timeout',
    book_id: 123,
    created_at: '2026-09-01T10:00:00Z',
  },
  {
    id: 3,
    platform: 'kindle' as const,
    episode_range: [1, 10] as [number, number],
    scheduled_at: '2026-10-03T10:00:00Z',
    status: 'completed' as const,
    error_message: null,
    book_id: 123,
    created_at: '2026-09-01T10:00:00Z',
  },
];

describe('Commercial Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('PlatformBadge renders correct platform name', () => {
    const { rerender } = render(<PlatformBadge platform="narou" />);
    expect(screen.getByText(/小説家になろう/i)).toBeInTheDocument();

    rerender(<PlatformBadge platform="kakuyomu" />);
    expect(screen.getByText(/カクヨム/i)).toBeInTheDocument();
  });

  test('PublicationScheduleTable renders schedules and action buttons correctly', () => {
    const onCancel = vi.fn();
    const onRunNow = vi.fn();
    const onError = vi.fn();

    render(
      <PublicationScheduleTable 
        schedules={mockSchedules} 
        onCancel={onCancel} 
        onRunNow={onRunNow} 
        onError={onError} 
      />
    );

    expect(screen.getByText('Run Now')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('No actions available')).toBeInTheDocument();
  });

  test('PublicationScheduleTable calls callbacks when buttons are clicked', () => {
    const onCancel = vi.fn();
    const onRunNow = vi.fn();
    const onError = vi.fn();

    render(
      <PublicationScheduleTable 
        schedules={mockSchedules} 
        onCancel={onCancel} 
        onRunNow={onRunNow} 
        onError={onError} 
      />
    );

    fireEvent.click(screen.getByText('Run Now'));
    expect(onRunNow).toHaveBeenCalledWith(1);

    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalledWith(1);

    fireEvent.click(screen.getByText('Retry'));
    expect(onRunNow).toHaveBeenCalledWith(2);

    fireEvent.click(screen.getByText('Error'));
    expect(onError).toHaveBeenCalledWith(2);
  });

  test('PublicationScheduleModal renders form and calls onSubmit', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <PublicationScheduleModal 
        bookId={123} 
        isOpen={true} 
        onClose={vi.fn()} 
        onSubmit={onSubmit} 
      />
    );

    expect(screen.getByText('新規予約投稿の作成')).toBeInTheDocument();
    fireEvent.click(screen.getByText('カクヨム'));
    fireEvent.click(screen.getByText('スケジュール登録'));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
        book_id: 123,
        platform: 'kakuyomu',
      }));
    });
  });

  test('PublicationErrorModal displays error message', () => {
    render(
      <PublicationErrorModal 
        isOpen={true} 
        onClose={vi.fn()} 
        errorMessage="Critical API Error" 
        scheduleId={456} 
      />
    );

    expect(screen.getByText('投稿エラー詳細')).toBeInTheDocument();
    expect(screen.getByText('Critical API Error')).toBeInTheDocument();
    expect(screen.getByText('456')).toBeInTheDocument();
  });

  test('CommercialPublishPanel fetches and displays schedules on mount', async () => {
    (commercialApi.getPublicationSchedules as any).mockResolvedValue(mockSchedules);

    render(<CommercialPublishPanel bookId={123} />);

    expect(screen.getByText('Loading schedules...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('小説家になろう')).toBeInTheDocument();
      expect(screen.getByText('カクヨム')).toBeInTheDocument();
    });

    expect(commercialApi.getPublicationSchedules).toHaveBeenCalledWith(123);
  });

  test('CommercialPublishPanel opens create modal and submits new schedule', async () => {
    (commercialApi.getPublicationSchedules as any).mockResolvedValue([]);
    (commercialApi.createPublicationSchedule as any).mockResolvedValue({ id: 100 });

    render(<CommercialPublishPanel bookId={123} />);

    // Wait for initial loading to complete so the submit button is enabled
    await waitFor(() => {
      expect(screen.queryByText('Loading schedules...')).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('新規予約投稿'));
    expect(screen.getByText('新規予約投稿の作成')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('submit-button'));

    await waitFor(() => {
      expect(commercialApi.createPublicationSchedule).toHaveBeenCalled();
    });
  });

  test('CommercialPublishPanel handles cancel schedule with confirmation', async () => {
    (commercialApi.getPublicationSchedules as any).mockResolvedValue([mockSchedules[0]]);
    (commercialApi.cancelPublicationSchedule as any).mockResolvedValue({ success: true });
    
    window.confirm = vi.fn().mockReturnValue(true);

    render(<CommercialPublishPanel bookId={123} />);

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Cancel'));

    await waitFor(() => {
      expect(commercialApi.cancelPublicationSchedule).toHaveBeenCalledWith(1);
    });
  });

  test('CommercialPublishPanel starts polling when a task is running', async () => {
    (commercialApi.getPublicationSchedules as any).mockResolvedValueOnce([
      { id: 1, platform: 'narou' as const, episode_range: [1, 1] as [number, number], scheduled_at: '', status: 'running' as const, error_message: null, book_id: 123, created_at: '2026-09-01T10:00:00Z' }
    ]);
    (commercialApi.getPublicationSchedules as any).mockResolvedValueOnce([
      { id: 1, platform: 'narou' as const, episode_range: [1, 1] as [number, number], scheduled_at: '', status: 'completed' as const, error_message: null, book_id: 123, created_at: '2026-09-01T10:00:00Z' }
    ]);

    vi.useFakeTimers();
    render(<CommercialPublishPanel bookId={123} />);

    // Trigger initial fetch and wait for it to resolve
    await vi.advanceTimersByTimeAsync(0);

    expect(commercialApi.getPublicationSchedules).toHaveBeenCalledTimes(1);

    // Advance timers to trigger polling
    await vi.advanceTimersByTimeAsync(5000);

    expect(commercialApi.getPublicationSchedules).toHaveBeenCalledTimes(2);

    vi.useRealTimers();
  });
});
