import { useState, useEffect, useCallback } from 'react';

export interface AgentThoughtStep {
  phase: string;
  step_name: string;
  detail_thought: string;
  progress_percent: number;
  timestamp: number;
}

interface UseGenerationProgressOptions {
  taskId?: string;
  onComplete?: () => void;
}

export function useGenerationProgress({ taskId, onComplete }: UseGenerationProgressOptions) {
  const [currentThought, setCurrentThought] = useState<AgentThoughtStep | null>(null);
  const [history, setHistory] = useState<AgentThoughtStep[]>([]);
  const [displayProgress, setDisplayProgress] = useState<number>(0);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // 進捗率の滑らかな補間アニメーション
  useEffect(() => {
    if (!currentThought) return;
    const target = currentThought.progress_percent;
    if (displayProgress === target) return;

    const timer = setInterval(() => {
      setDisplayProgress((prev) => {
        if (prev < target) {
          const next = prev + 2;
          return next > target ? target : next;
        } else if (prev > target) {
          const next = prev - 2;
          return next < target ? target : next;
        }
        return prev;
      });
    }, 20);

    return () => clearInterval(timer);
  }, [currentThought?.progress_percent, displayProgress]);

  // SSEイベント接続
  useEffect(() => {
    if (!taskId) return;

    setIsGenerating(true);
    const eventSource = new EventSource(`/api/tasks/${taskId}/stream`);

    eventSource.addEventListener('progress', (event: MessageEvent) => {
      try {
        const step: AgentThoughtStep = JSON.parse(event.data);
        setCurrentThought(step);
        setHistory((prev) => [...prev, step]);
        if (step.progress_percent >= 100) {
          setIsGenerating(false);
          if (onComplete) onComplete();
        }
      } catch (err) {
        console.error('Failed to parse progress event:', err);
      }
    });

    eventSource.onerror = () => {
      eventSource.close();
      setIsGenerating(false);
    };

    return () => {
      eventSource.close();
    };
  }, [taskId, onComplete]);

  return {
    currentThought,
    history,
    displayProgress,
    isGenerating,
  };
}
