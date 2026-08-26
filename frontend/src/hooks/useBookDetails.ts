import { useCallback } from 'react';
import {
  getPlots,
  getChapters,
  getBible,
  getOptHistory,
  getPendingPatches,
  getPromptVersions,
  getNarrativeMetricsTrend,
} from '../api';
import { useBookStore } from '../store/useBookStore';
import { useUIStore } from '../store/useUIStore';

export function useBookDetails(_bookId: number | null) {
  const { setPlots, setChapters, setBible } = useBookStore();
  const { setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend } = useUIStore();

  const loadBookDetails = useCallback(async (bookId: number) => {
    try {
      // Fetch all relevant data in parallel
      const [plotsData, chData, bibleData, histData, patchData, promptData, trendData] = await Promise.all([
        getPlots(bookId),
        getChapters(bookId),
        getBible(bookId),
        getOptHistory(bookId),
        getPendingPatches(bookId),
        getPromptVersions(bookId),
        getNarrativeMetricsTrend(bookId),
      ]);
      setPlots(plotsData);
      setChapters(chData);
      setBible(bibleData);
      setOptHistory(histData);
      setPendingPatches(patchData);
      setPromptVersions(promptData);
      setMetricTrend(trendData);
    } catch (error) {
      console.error('Failed to load book details:', error);
      // Optionally, we could set an error state in the store
    }
  }, [setPlots, setChapters, setBible, setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend]);

  return { loadBookDetails };
}