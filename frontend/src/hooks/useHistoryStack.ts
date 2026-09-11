import { useCallback, useRef, useState } from "react";

export const useHistoryStack = () => {
  const [past, setPast] = useState<string[]>([]);
  const [future, setFuture] = useState<string[]>([]);
  const [present, setPresent] = useState<string>("");

  const MAX_STACK = 50;

  const pushState = useCallback((text: string) => {
    // If the new text is same as present, do nothing? 
    // But we might want to push anyway? Usually we push when text changes.
    // We'll push only if different from present to avoid duplicates.
    if (text === present) return;
    setPast((prev) => {
      const newPast = [...prev, present];
      // Keep only last MAX_STACK
      if (newPast.length > MAX_STACK) {
        newPast.shift();
      }
      return newPast;
    });
    setFuture([]);
    setPresent(text);
  }, [present]);

  const undo = useCallback((): string | null => {
    if (past.length === 0) return null;
    const previous = past[past.length - 1];
    if (previous === undefined) return null;
    const newPast = past.slice(0, past.length - 1);
    setPast(newPast);
    setFuture([present, ...future]);
    setPresent(previous);
    return previous;
  }, [past, present, future]);

  const redo = useCallback((): string | null => {
    if (future.length === 0) return null;
    const next = future[0];
    if (next === undefined) return null;
    const newFuture = future.slice(1);
    setFuture(newFuture);
    setPast([...past, present]);
    setPresent(next);
    return next;
  }, [past, present, future]);

  const canUndo = past.length > 0;
  const canRedo = future.length > 0;

  return { past, future, present, pushState, undo, redo, canUndo, canRedo };
};