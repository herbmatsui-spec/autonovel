import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { TaskStatus } from '../types';

interface TaskState {
  activeTaskId: string | null;
  taskStatus: TaskStatus | null;
  setActiveTaskId: (id: string | null) => void;
  setTaskStatus: (status: TaskStatus | null) => void;
  clearTask: () => void;
}

export const useTaskStore = create<TaskState>()(
  persist(
    (set) => ({
      activeTaskId: null,
      taskStatus: null,
      setActiveTaskId: (id) => set({ activeTaskId: id }),
      setTaskStatus: (status) => set({ taskStatus: status }),
      clearTask: () => set({ activeTaskId: null, taskStatus: null }),
    }),
    {
      name: 'task-storage',
      partialize: (state) => ({
        activeTaskId: state.activeTaskId,
      }),
      version: 1,
    }
  )
);
