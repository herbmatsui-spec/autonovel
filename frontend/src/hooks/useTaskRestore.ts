import { useEffect } from 'react';
import { getTaskStatus } from '@/api';
import { useTaskStore } from '@/store/useTaskStore';

export function useTaskRestore() {
  const { activeTaskId, setTaskStatus, clearTask } = useTaskStore();

  useEffect(() => {
    if (!activeTaskId) return;

    let mounted = true;

    const restoreTask = async () => {
      try {
        const status = await getTaskStatus(activeTaskId);
        if (!mounted) return;

        if (status.is_running) {
          setTaskStatus(status);
        } else {
          clearTask();
        }
      } catch {
        if (mounted) {
          clearTask();
        }
      }
    };

    restoreTask();

    return () => {
      mounted = false;
    };
  }, [activeTaskId, setTaskStatus, clearTask]);
}