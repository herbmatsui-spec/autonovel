import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ManuscriptCountBadge } from '@/components/editor/ManuscriptCountBadge';
import { ManuscriptTargetIndicator } from '@/components/editor/ManuscriptTargetIndicator';
import { ManuscriptCountResult, CountMode } from '@/types/manuscript';

const mockCount: ManuscriptCountResult = {
  body: 12345,
  withRuby: 15678,
  publishing: 30.9,
  pages: 31,
  lines: 309,
  readingTimeMinutes: 31,
};

describe('ManuscriptCountBadge', () => {
  it('renders with default props', () => {
    const onModeChange = vi.fn();
    render(<ManuscriptCountBadge count={mockCount} mode="body" onModeChange={onModeChange} />);
    
    expect(screen.getByTestId('manuscript-count-value')).toHaveTextContent('本文 12,345 字');
    expect(screen.getByTestId('mode-body-btn')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('mode-with-ruby-btn')).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('mode-publishing-btn')).toHaveAttribute('aria-pressed', 'false');
  });

  it('switches mode when button clicked', () => {
    const onModeChange = vi.fn();
    render(<ManuscriptCountBadge count={mockCount} mode="body" onModeChange={onModeChange} />);
    
    fireEvent.click(screen.getByTestId('mode-with-ruby-btn'));
    expect(onModeChange).toHaveBeenCalledWith('withRuby');
    
    fireEvent.click(screen.getByTestId('mode-publishing-btn'));
    expect(onModeChange).toHaveBeenCalledWith('publishing');
  });

  it('displays correct text for each mode', () => {
    const onModeChange = vi.fn();
    const { rerender } = render(<ManuscriptCountBadge count={mockCount} mode="body" onModeChange={onModeChange} />);
    
    expect(screen.getByTestId('manuscript-count-value')).toHaveTextContent('本文 12,345 字');
    
    rerender(<ManuscriptCountBadge count={mockCount} mode="withRuby" onModeChange={onModeChange} />);
    expect(screen.getByTestId('manuscript-count-value')).toHaveTextContent('ルビ込 15,678 字');
    
    rerender(<ManuscriptCountBadge count={mockCount} mode="publishing" onModeChange={onModeChange} />);
    expect(screen.getByTestId('manuscript-count-value')).toHaveTextContent('原稿 30.9 枚 (31枚)');
  });

  it('shows tooltip with detailed breakdown', () => {
    const onModeChange = vi.fn();
    render(<ManuscriptCountBadge count={mockCount} mode="body" onModeChange={onModeChange} />);
    
    const badge = screen.getByRole('group');
    expect(badge).toHaveAttribute('title', '純本文: 12,345字 | ルビ込: 15,678字 | 400字原稿: 約31枚 (読了: 約31分)');
  });

  it('applies compact mode styling', () => {
    const onModeChange = vi.fn();
    const { container } = render(<ManuscriptCountBadge count={mockCount} mode="body" onModeChange={onModeChange} compact />);
    
    const badge = container.querySelector('.manuscript-count-badge');
    expect(badge).toHaveStyle({ fontSize: '0.75rem', padding: '2px 6px' });
  });

  it('has correct accessibility attributes', () => {
    const onModeChange = vi.fn();
    render(<ManuscriptCountBadge count={mockCount} mode="body" onModeChange={onModeChange} />);
    
    const group = screen.getByRole('group');
    expect(group).toHaveAttribute('aria-label', '文字数カウントモード');
  });
});

describe('ManuscriptCountBadge + ManuscriptTargetIndicator integration', () => {
  const integrationCount: ManuscriptCountResult = {
    body: 10800, // Under 12000 target
    withRuby: 12000,
    publishing: 27.0,
    pages: 27,
    lines: 270,
    readingTimeMinutes: 27,
  };
  
  it('both components render with same count data', () => {
    const onModeChange = vi.fn();
    const onPresetChange = vi.fn();
    
    render(
      <div>
        <ManuscriptCountBadge count={integrationCount} mode="body" onModeChange={onModeChange} />
        <ManuscriptTargetIndicator
          count={integrationCount}
          selectedPresetId="shousetsu-gekkan"
          onPresetChange={onPresetChange}
        />
      </div>
    );
    
    expect(screen.getByTestId('manuscript-count-value')).toBeInTheDocument();
    expect(screen.getByTestId('preset-select')).toBeInTheDocument();
    expect(screen.getByTestId('target-progress-text')).toBeInTheDocument();
  });

  it('preset change updates progress bar', () => {
    const onModeChange = vi.fn();
    const onPresetChange = vi.fn();
    
    render(
      <div>
        <ManuscriptCountBadge count={integrationCount} mode="body" onModeChange={onModeChange} />
        <ManuscriptTargetIndicator
          count={integrationCount}
          selectedPresetId="shousetsu-gekkan"
          onPresetChange={onPresetChange}
        />
      </div>
    );
    
    // Initial preset (shousetsu-gekkan: 12000 chars)
    expect(screen.getByTestId('target-progress-text')).toHaveTextContent('10,800 / 12,000 字');
    
    // Change to shousetsu-subaru (20000 chars)
    fireEvent.change(screen.getByTestId('preset-select'), { target: { value: 'shousetsu-subaru' } });
    expect(onPresetChange).toHaveBeenCalledWith('shousetsu-subaru');
  });
});

describe('localStorage persistence simulation', () => {
  it('count mode persists across remounts', () => {
    const onModeChange = vi.fn();
    const { rerender } = render(<ManuscriptCountBadge count={mockCount} mode="body" onModeChange={onModeChange} />);
    
    // Simulate user changing mode
    fireEvent.click(screen.getByTestId('mode-publishing-btn'));
    expect(onModeChange).toHaveBeenCalledWith('publishing');
    
    // Simulate remount with persisted mode
    rerender(<ManuscriptCountBadge count={mockCount} mode="publishing" onModeChange={onModeChange} />);
    expect(screen.getByTestId('mode-publishing-btn')).toHaveAttribute('aria-pressed', 'true');
  });
});