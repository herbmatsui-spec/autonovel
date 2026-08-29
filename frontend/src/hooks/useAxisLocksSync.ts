import { useEffect } from 'react';
import { sseClient } from '@/lib/sseClient';
import { useBookStore } from '@/store/useBookStore';

export function useAxisLocksSync(): void {
  const { axisSelections, setAxisLock } = useBookStore();

  useEffect(() => {
    const unsubscribe = sseClient.subscribe((eventType, data) => {
      if (eventType === 'axis_locks') {
        const payload = data as { book_id: number; axis_lock_flags: Record<string, boolean> };
        // Only update if the current selected book matches
        const selectedBook = useBookStore.getState().selectedBook;
        if (selectedBook && selectedBook.id === payload.book_id) {
          for (const [axis, locked] of Object.entries(payload.axis_lock_flags)) {
            // axis is string, need to cast to AxisType
            setAxisLock(axis as any, locked);
          }
        }
      }
    });
    return () => unsubscribe();
  }, [setAxisLock]);
}