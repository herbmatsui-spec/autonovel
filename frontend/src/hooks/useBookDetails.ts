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

export function useBookDetails(bookId?: number | null) {
  const { setPlots, setChapters, setBible } = useBookStore();
  const { setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend } = useUIStore();

  const loadBookDetails = useCallback(async (targetBookId?: number | null) => {
    const id = targetBookId ?? bookId;
    if (!id) return;
    try {
      // Fetch all relevant data in parallel
      const [plotsData, chData, bibleData, histData, patchData, promptData, trendData] = await Promise.all([
        getPlots(id),
        getChapters(id),
        getBible(id),
        getOptHistory(id),
        getPendingPatches(id),
        getPromptVersions(id),
        getNarrativeMetricsTrend(id),
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
    }
  }, [bookId, setPlots, setChapters, setBible, setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend]);

  return { loadBookDetails };
}