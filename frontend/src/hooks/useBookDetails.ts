import { useCallback } from 'react';
import {
  getPlots,
  getChapters,
  getBible,
  getOptHistory,
  getPendingPatches,
  getPromptVersions,
  getNarrativeMetricsTrend,
  getStoryCanvas,
} from '../api';
import { useBookStore } from '../store/useBookStore';
import { useUIStore } from '../store/useUIStore';
import { useStoryCanvasStore } from '../store/useStoryCanvasStore';

export function useBookDetails(bookId?: number | null) {
  const { setPlots, setChapters, setBible } = useBookStore();
  const { setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend } = useUIStore();
  const { applyServerNodes, applyServerEdges, setLoading: setCanvasLoading } = useStoryCanvasStore();

  const loadBookDetails = useCallback(async (targetBookId?: number | null) => {
    const id = targetBookId ?? bookId;
    if (!id) return;
    try {
      setCanvasLoading(true);
      // Fetch all relevant data in parallel
      const [plotsData, chData, bibleData, histData, patchData, promptData, trendData, canvasData] = await Promise.all([
        getPlots(id),
        getChapters(id),
        getBible(id),
        getOptHistory(id),
        getPendingPatches(id),
        getPromptVersions(id),
        getNarrativeMetricsTrend(id),
        getStoryCanvas(id),
      ]);
      setPlots(plotsData);
      setChapters(chData);
      setBible(bibleData);
      setOptHistory(histData);
      setPendingPatches(patchData);
      setPromptVersions(promptData);
      setMetricTrend(trendData);
      applyServerNodes(canvasData.nodes);
      applyServerEdges(canvasData.edges);
    } catch (error) {
      console.error('Failed to load book details:', error);
    } finally {
      setCanvasLoading(false);
    }
  }, [bookId, setPlots, setChapters, setBible, setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend, applyServerNodes, applyServerEdges, setCanvasLoading]);

  return { loadBookDetails };
}