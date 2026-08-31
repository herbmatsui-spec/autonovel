import { useState, useCallback } from "react";
import { ToastNotification } from "../types";

export function useToast() {
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: "success" | "error" | "info" = "info", durationMs: number = 4000) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastNotification = { id, type, message, durationMs };

      setToasts((prev) => [...prev, newToast]);

      if (durationMs > 0) {
        setTimeout(() => {
          removeToast(id);
        }, durationMs);
      }
    },
    [removeToast]
  );

  return { toasts, addToast, removeToast };
}
