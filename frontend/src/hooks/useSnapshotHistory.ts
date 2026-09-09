import { useCallback, useEffect, useState } from "react";
import { EditorSnapshot } from "../types/history";

export const useSnapshotHistory = (bookId: string | number, epNum: string | number) => {
  const [snapshots, setSnapshots] = useState<EditorSnapshot[]>([]);

  const storageKey = `autonovel.snapshots.${bookId}.${epNum}`;

  // Load snapshots from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSnapshots(parsed);
      } catch (e) {
        console.error("Failed to parse snapshots from localStorage", e);
        setSnapshots([]);
      }
    }
  }, [storageKey]);

  // Save snapshots to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(snapshots));
  }, [snapshots, storageKey]);

  const takeSnapshot = useCallback((
    label: string,
    text: string,
    source: EditorSnapshot['source']
  ) => {
    const snapshot: EditorSnapshot = {
      id: Math.random().toString(36).substring(2, 15),
      ep_num: Number(epNum),
      timestamp: Date.now(),
      label,
      text,
      charCount: text.length,
      source
    };
    setSnapshots(prev => {
      const newSnapshots = [snapshot, ...prev];
      // Keep only last 20
      if (newSnapshots.length > 20) {
        newSnapshots.pop();
      }
      return newSnapshots;
    });
  }, [epNum]);

  const restoreSnapshot = useCallback((id: string): string | null => {
    const snapshot = snapshots.find(snap => snap.id === id);
    if (!snapshot) return null;
    // Optionally, we could remove the snapshot after restore? Not specified.
    // We'll just return the text.
    return snapshot.text;
  }, [snapshots]);

  const deleteSnapshot = useCallback((id: string) => {
    setSnapshots(prev => prev.filter(snap => snap.id !== id));
  }, []);

  return { snapshots, takeSnapshot, restoreSnapshot, deleteSnapshot };
};