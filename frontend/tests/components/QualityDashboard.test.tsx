import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NovelProvider } from '../../src/context/NovelContext';
import { BookScoreRadarChart } from '../../src/components/studio/BookScoreRadarChart';
import { QualityDashboardModal } from '../../src/components/studio/QualityDashboardModal';
import * as qualityApi from '../../src/api/quality';
import * as booksApi from '../../src/api/books';
import { vi } from 'vitest';

vi.mock('../../src/api/quality', () => ({
  fetchChapterBookScore: vi.fn(),
  fetchBookScoreHistory: vi.fn(),
  fetchPDCACycles: vi.fn(),
}));

vi.mock('../../src/api/books', () => ({
  fetchBookById: vi.fn().mockResolvedValue({ id: 1, title: 'Mock Book' }),
  fetchBooks: vi.fn().mockResolvedValue([]),
}));

const mockBookScore = {
  overall_score: 85.5,
  dimensions: {
    structure: 80,
    coherency: 90,
    factual: 85,
    visual: 80,
    reader: 90,
  },
  benchmark: {
    structure: 70,
    coherency: 70,
    factual: 70,
    visual: 70,
    reader: 70,
  },
  previous: {
    structure: 75,
    coherency: 85,
    factual: 80,
    visual: 75,
    reader: 85,
  },
};

const mockHistory = [
  { chapter_number: 1, overall_score: 70 },
  { chapter_number: 2, overall_score: 75 },
  { chapter_number: 3, overall_score: 85.5 },
];

const mockPDCA = [
  {
    cycle_index: 1,
    snapshot: {
      overall_score: 75,
      directives: [
        { dimension: "structure", severity: "medium", rationale: "Pacing is slow", directive: "Tighten the middle act" },
      ],
      before_text: "Old text",
      after_text: "New improved text",
    },
  },
];

describe('Quality Dashboard Components', () => {
  const renderWithContext = (ui: React.ReactElement) => {
    return render(
      <NovelProvider>
        {ui}
      </NovelProvider>
    );
  };

  describe('BookScoreRadarChart', () => {
    it('renders the radar chart with correct dimensions', () => {
      render(
        <BookScoreRadarChart
          scores={mockBookScore.dimensions}
          previousScores={mockBookScore.previous}
          benchmark={mockBookScore.benchmark}
        />
      );
      
      // Check if SVG is rendered
      const svg = screen.getByRole('img', { hidden: true }); // Radar chart uses <svg role="img"> or similar
      expect(svg).toBeDefined();
      
      // Check for dimension labels
      expect(screen.getByText(/構造/i)).toBeDefined();
      expect(screen.getByText(/一貫性/i)).toBeDefined();
      expect(screen.getByText(/事実正確性/i)).toBeDefined();
      expect(screen.getByText(/視覚的相乗効果/i)).toBeDefined();
      expect(screen.getByText(/読者体験/i)).toBeDefined();
    });

    it('renders legend for current, previous and benchmark', () => {
      render(
        <BookScoreRadarChart
          scores={mockBookScore.dimensions}
          previousScores={mockBookScore.previous}
          benchmark={mockBookScore.benchmark}
        />
      );
      expect(screen.getByText(/現サイクル/i)).toBeDefined();
      expect(screen.getByText(/前サイクル/i)).toBeDefined();
      expect(screen.getByText(/ベンチマーク/i)).toBeDefined();
    });
  });

  describe('QualityDashboardModal', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('fetches and displays quality data on mount', async () => {
      (qualityApi.fetchChapterBookScore as any).mockResolvedValue(mockBookScore);
      (qualityApi.fetchBookScoreHistory as any).mockResolvedValue(mockHistory);
      (qualityApi.fetchPDCACycles as any).mockResolvedValue(mockPDCA);

      renderWithContext(
        <QualityDashboardModal 
          bookId={1} 
          chapterNumber={3} 
          onClose={() => {}} 
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/総合スコア/i)).toBeDefined();
        expect(screen.getByText(/85.5/i)).toBeDefined();
      });

      expect(qualityApi.fetchChapterBookScore).toHaveBeenCalledWith(1, 3);
      expect(qualityApi.fetchBookScoreHistory).toHaveBeenCalledWith(1);
      expect(qualityApi.fetchPDCACycles).toHaveBeenCalledWith(1, 3);
    });

    it('handles API errors gracefully', async () => {
      (qualityApi.fetchChapterBookScore as any).mockRejectedValue(new Error('API Error'));
      (qualityApi.fetchBookScoreHistory as any).mockResolvedValue(mockHistory);
      (qualityApi.fetchPDCACycles as any).mockResolvedValue(mockPDCA);

      renderWithContext(
        <QualityDashboardModal 
          bookId={1} 
          chapterNumber={3} 
          onClose={() => {}} 
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/データの取得に失敗しました/i)).toBeDefined();
      });
    });

    it('calls onClose when close button is clicked', async () => {
      const onCloseMock = vi.fn();
      (qualityApi.fetchChapterBookScore as any).mockResolvedValue(mockBookScore);
      (qualityApi.fetchBookScoreHistory as any).mockResolvedValue(mockHistory);
      (qualityApi.fetchPDCACycles as any).mockResolvedValue(mockPDCA);

      renderWithContext(
        <QualityDashboardModal 
          bookId={1} 
          chapterNumber={3} 
          onClose={onCloseMock} 
        />
      );

      const closeBtn = screen.getByRole('button', { name: /閉じる/i });
      fireEvent.click(closeBtn);
      expect(onCloseMock).toHaveBeenCalled();
    });

    it('navigates between chapters', async () => {
      (qualityApi.fetchChapterBookScore as any).mockResolvedValue(mockBookScore);
      (qualityApi.fetchBookScoreHistory as any).mockResolvedValue(mockHistory);
      (qualityApi.fetchPDCACycles as any).mockResolvedValue(mockPDCA);

      renderWithContext(
        <QualityDashboardModal 
          bookId={1} 
          chapterNumber={3} 
          onClose={() => {}} 
        />
      );

      const nextBtn = screen.getByRole('button', { name: /Next/i });
      fireEvent.click(nextBtn);

      await waitFor(() => {
        expect(qualityApi.fetchChapterBookScore).toHaveBeenCalledWith(1, 4);
      });
    });
  });
});
