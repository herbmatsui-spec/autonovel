import { useState, useEffect, useCallback, useRef } from "react";

export type SaveStatus = "saved" | "saving" | "unsaved";

export function useAutosave(content: string, delay: number = 1000) {
  const [status, setStatus] = useState<SaveStatus>("saved");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const contentRef = useRef(content);

  contentRef.current = content;

  const save = useCallback(() => {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem("autonovel_autosave", contentRef.current);
      setLastSavedAt(new Date());
      setStatus("saved");
    } catch (e) {
      console.warn("Autosave failed:", e);
    }
  }, []);

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

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem("autonovel_autosave");
    if (saved) setLastSavedAt(new Date());
  }, []);

  return { status, lastSavedAt, save };
}