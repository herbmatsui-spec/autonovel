import { useEffect, useRef } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { stopTask } from '../api';

export function useTaskMonitor() {
  const { activeTaskId, taskStatus, setActiveTaskId, setTaskStatus } = useTaskStore();
  const logEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [taskStatus?.logs]);

  const handleStopTask = async () => {
    if (!activeTaskId) return;
    try {
      await stopTask(activeTaskId);
    } catch (err) {
      console.error('Failed to stop task:', err);
    } finally {
      setActiveTaskId(null);
      setTaskStatus(null);
    }
  };

  return {
    activeTaskId,
    taskStatus,
    logEndRef,
    handleStopTask,
  };
}
