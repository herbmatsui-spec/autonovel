import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ManuscriptTargetIndicator } from '@/components/editor/ManuscriptTargetIndicator';
import { ManuscriptCountResult } from '@/types/manuscript';
import { checkTarget } from '@/utils/manuscriptCount';

const mockCount: ManuscriptCountResult = {
  body: 10800,
  withRuby: 12000,
  publishing: 27.0,
  pages: 27,
  lines: 270,
  readingTimeMinutes: 27,
};

const overCount: ManuscriptCountResult = {
  body: 12001,
  withRuby: 13500,
  publishing: 30.0,
  pages: 31,
  lines: 301,
  readingTimeMinutes: 31,
};

describe('ManuscriptTargetIndicator', () => {
  it('renders with default preset', () => {
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={mockCount}
        selectedPresetId="shousetsu-gekkan"
        onPresetChange={onPresetChange}
        customTargetChars={10000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    expect(screen.getByTestId('preset-select')).toHaveValue('shousetsu-gekkan');
    expect(screen.getByTestId('target-progress-text')).toBeInTheDocument();
  });

  it('shows warning state at 90% threshold', () => {
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={mockCount}
        selectedPresetId="shousetsu-gekkan"
        onPresetChange={onPresetChange}
        customTargetChars={10000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    // 10800 / 12000 = 0.9 (90%) - should show warning
    expect(screen.getByTestId('target-progress-text')).toHaveTextContent('10,800 / 12,000 字 (90%)');
    expect(screen.getByTestId('target-progress-text')).toHaveTextContent('あと 1,200 字');
  });

  it('shows over state when exceeding target', () => {
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={overCount}
        selectedPresetId="shousetsu-gekkan"
        onPresetChange={onPresetChange}
        customTargetChars={10000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    expect(screen.getByTestId('target-progress-text')).toHaveTextContent('目標超過 +1 字');
  });

  it('shows max over state for presets with maxPages', () => {
    const maxCount: ManuscriptCountResult = {
      body: 41000,
      withRuby: 45000,
      publishing: 102.5,
      pages: 103,
      lines: 1025,
      readingTimeMinutes: 103,
    };
    
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={maxCount}
        selectedPresetId="dengeki-bunko"
        onPresetChange={onPresetChange}
        customTargetChars={10000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    // dengeki-bunko has maxPages: 100, current pages: 103
    expect(screen.getByTestId('target-progress-text')).toHaveTextContent('上限 100枚 超過 (現在 103枚)');
  });

  it('shows custom input when custom preset selected', () => {
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={mockCount}
        selectedPresetId="custom"
        onPresetChange={onPresetChange}
        customTargetChars={15000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    const input = screen.getByDisplayValue(15000);
    expect(input).toBeInTheDocument();
    
    fireEvent.change(input, { target: { value: '20000' } });
    expect(onCustomTargetChange).toHaveBeenCalledWith(20000);
  });

  it('has correct accessibility attributes for progress bar', () => {
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={mockCount}
        selectedPresetId="shousetsu-gekkan"
        onPresetChange={onPresetChange}
        customTargetChars={10000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '10800');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '12000');
  });

  it('calls onPresetChange when preset selected', () => {
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={mockCount}
        selectedPresetId="shousetsu-gekkan"
        onPresetChange={onPresetChange}
        customTargetChars={10000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    fireEvent.change(screen.getByTestId('preset-select'), { target: { value: 'shousetsu-subaru' } });
    expect(onPresetChange).toHaveBeenCalledWith('shousetsu-subaru');
  });

  it('shows narou preset with no target (unlimited)', () => {
    const onPresetChange = vi.fn();
    const onCustomTargetChange = vi.fn();
    
    render(
      <ManuscriptTargetIndicator
        count={mockCount}
        selectedPresetId="narou"
        onPresetChange={onPresetChange}
        customTargetChars={10000}
        onCustomTargetChange={onCustomTargetChange}
      />
    );
    
    // narou has targetChars: 0, should not show progress bar
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });
});