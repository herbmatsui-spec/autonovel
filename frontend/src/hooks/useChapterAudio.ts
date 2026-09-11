import { useState, useEffect, useCallback } from "react";
import { fetchChapterAudio, triggerAudioSynthesis } from "../api/audio";
import { AudioTrackInfo } from "../types/multimedia";

export function useChapterAudio(bookId: number | null, episodeNum: number | null) {
  const [audioTrack, setAudioTrack] = useState<AudioTrackInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [synthesizing, setSynthesizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAudio = useCallback(async () => {
    if (!bookId || !episodeNum) {
      setAudioTrack(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const track = await fetchChapterAudio(bookId, episodeNum);
      setAudioTrack(track);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audio");
    } finally {
      setLoading(false);
    }
  }, [bookId, episodeNum]);

  useEffect(() => {
    void loadAudio();
  }, [loadAudio]);

  const synthesize = useCallback(
    async (chapterText?: string, characters?: string[]) => {
      if (!bookId || !episodeNum) return null;
      setSynthesizing(true);
      setError(null);
      try {
        const res = await triggerAudioSynthesis({
          book_id: bookId,
          episode_num: episodeNum,
          chapter_text: chapterText,
          characters: characters,
        });
        // 即座に再読み込み試行
        await loadAudio();
        return res;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Synthesis failed");
        return null;
      } finally {
        setSynthesizing(false);
      }
    },
    [bookId, episodeNum, loadAudio]
  );

  return {
    audioTrack,
    loading,
    synthesizing,
    error,
    refresh: loadAudio,
    synthesize,
  };
}
