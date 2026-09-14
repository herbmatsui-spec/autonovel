import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { PDCALiveMonitor } from '../PDCALiveMonitor';

describe('PDCALiveMonitor', () => {
  it('renders title and initial states without crashing', () => {
    render(<PDCALiveMonitor bookId={1} />);
    expect(screen.getByText(/PDCA & リアルタイムライブモニター/i)).toBeInTheDocument();
    expect(screen.getByText(/初期スコア/i)).toBeInTheDocument();
    expect(screen.getByText(/現在スコア/i)).toBeInTheDocument();
  });
});
