import { useState, useEffect, useCallback } from "react";

export function useLocalDraft(key: string, initial: string) {
  const [content, setContent] = useState(() => {
    if (typeof window === "undefined") return initial;
    const saved = localStorage.getItem(key);
    return saved ? saved : initial;
  });

  useEffect(() => {
    const id = setInterval(() => {
      localStorage.setItem(key, content);
    }, 2000);
    return () => clearInterval(id);
  }, [content, key]);

  const clearDraft = useCallback(() => {
    localStorage.removeItem(key);
    setContent(initial);
  }, [key, initial]);

  return [content, setContent, clearDraft] as const;
}