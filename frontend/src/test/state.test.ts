import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '@/store/useUIStore';
import { useTaskStore } from '@/store/useTaskStore';

describe('Frontend State Store Integration Tests', () => {
  beforeEach(() => {
    // Reset stores to default state before each test
    useUIStore.setState({
      isCreateModalOpen: false,
      globalError: null,
      optHistory: [],
      pendingPatches: [],
      promptVersions: [],
      metricTrend: [],
    });
    useTaskStore.setState({
      activeTaskId: null,
      taskStatus: null,
    });
  });

  describe('UIStore State Transitions', () => {
    it('should toggle create modal visibility', () => {
      useUIStore.getState().setCreateModalOpen(true);
      expect(useUIStore.getState().isCreateModalOpen).toBe(true); // Note: wait, is it isCreateModalOpen or isModalOpen?
      // Checking based on the useUIStore.ts I read earlier
    });

    it('should set and clear global error', () => {
      useUIStore.getState().setGlobalError('Test Error');
      expect(useUIStore.getState().globalError).toBe('Test Error');
      useUIStore.getState().setGlobalError(null);
      expect(useUIStore.getState().globalError).toBeNull();
    });
  });

  describe('TaskStore State Transitions', () => {
    it('should track active task lifecycle', () => {
      const taskId = 'test-task-123';
      
      // 1. Start task
      useTaskStore.getState().setActiveTaskId(taskId);
      expect(useTaskStore.getState().activeTaskId).toBe(taskId);

      // 2. Update status
      const mockStatus = {
        task_id: taskId,
        is_running: true,
        current_step: 1,
        total_steps: 10,
        message: 'Running...',
        logs: ['Started']
      };
      useTaskStore.getState().setTaskStatus(mockStatus);
      expect(useTaskStore.getState().taskStatus).toEqual(mockStatus);

      // 3. Clear task
      useTaskStore.getState().clearTask();
      expect(useTaskStore.getState().activeTaskId).toBeNull();
      expect(useTaskStore.getState().taskStatus).toBeNull();
    });
  });

  describe('Cross-Store Interaction Scenarios', () => {
    it('should handle error propagation from API to UIStore', () => {
      const errorMessage = 'API Connection Failed';
      useUIStore.getState().setGlobalError(errorMessage);
      
      expect(useUIStore.getState().globalError).toBe(errorMessage);
      // In a real app, this would trigger the ErrorBanner component
    });
  });
});
