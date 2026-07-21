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

export function useBookDetails(_bookId: number | null, activeTab: string) {
  const { setPlots, setChapters, setBible } = useBookStore();
  const { setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend } = useUIStore();

const loadBookDetails = useCallback(async (bookId: number) => {
    try {
      if (activeTab === 'plots') {
        const data = await getPlots(bookId);
        setPlots(data);
      } else if (activeTab === 'write') {
        const chData = await getChapters(bookId);
        setChapters(chData);
        const bibleData = await getBible(bookId);
        setBible(bibleData);
      } else if (activeTab === 'analytics') {
        const histData = await getOptHistory(bookId);
        setOptHistory(histData);
        const patchesData = await getPendingPatches(bookId);
        setPendingPatches(patchesData);
        const versionsData = await getPromptVersions(bookId);
        setPromptVersions(versionsData);

        try {
          const trendData = await getNarrativeMetricsTrend(bookId, 1);
          setMetricTrend(trendData);
        } catch (e) {
          console.error('Error loading narrative metrics:', e);
        }
      }
    } catch (err: any) {
      console.error('Error loading book details:', err);
    }
  }, [activeTab, setPlots, setChapters, setBible, setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend]);

  return { loadBookDetails };
}
