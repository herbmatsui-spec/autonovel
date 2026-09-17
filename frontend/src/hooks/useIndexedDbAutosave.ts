import { useState, useEffect, useRef, useCallback } from "react";
import { AutoSaveStatus, EditorSnapshot } from "../types/editorSnapshot";
import { indexedDbClient } from "../lib/storage/indexedDbClient";
import { useNetworkStatus } from "./useNetworkStatus";

export function useIndexedDbAutosave(
  bookId: string | number,
  episodeId: string | number,
  content: string,
  delay: number = 500
) {
  const isOnline = useNetworkStatus();
  const [status, setStatus] = useState<AutoSaveStatus>("saved");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const save = useCallback(async () => {
    try {
      const snapshot: EditorSnapshot = {
        key: indexedDbClient.makeKey(bookId, episodeId),
        bookId,
        episodeId,
        content,
        charCount: content.length,
        updatedAt: Date.now(),
      };
      await indexedDbClient.saveSnapshot(snapshot);
      setLastSavedAt(new Date());
      setStatus(isOnline ? "saved" : "offline");
    } catch (err) {
      console.warn("IndexedDB autosave failed:", err);
      setStatus("unsaved");
    }
  }, [bookId, episodeId, content, isOnline]);

  useEffect(() => {
    setStatus("unsaved");
    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    timeoutRef.current = setTimeout(() => {
      setStatus("saving");
      save();
    }, delay);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [content, delay, save]);

  return { status, lastSavedAt, save };
}