import { create } from 'zustand';
import { AgentStatusEvent, PipelineProgressEvent } from '../lib/sseClient';

export interface AgentLogItem {
  id: string;
  timestamp: string;
  agent: string;
  phase: string;
  message: string;
  score?: number;
  isApproved?: boolean;
}

interface AgentLiveState {
  isConnected: boolean;
  currentAgent: string | null;
  currentPhase: string | null;
  overallProgress: number;
  statusMessage: string;
  logs: AgentLogItem[];
  
  setConnected: (connected: boolean) => void;
  handleAgentStatus: (event: AgentStatusEvent) => void;
  handlePipelineProgress: (event: PipelineProgressEvent) => void;
  clearLogs: () => void;
}

export const useAgentLiveStore = create<AgentLiveState>((set) => ({
  isConnected: false,
  currentAgent: null,
  currentPhase: null,
  overallProgress: 0,
  statusMessage: '待機中',
  logs: [],

  setConnected: (connected) => set({ isConnected: connected }),

  handleAgentStatus: (event) =>
    set((state) => {
      const newLog: AgentLogItem = {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
        agent: event.agent,
        phase: event.phase,
        message: event.message,
        score: event.score,
        isApproved: event.is_approved,
      };

      return {
        currentAgent: event.agent,
        currentPhase: event.phase,
        statusMessage: event.message,
        logs: [newLog, ...state.logs].slice(0, 50), // 最新50件保持
      };
    }),

  handlePipelineProgress: (event) =>
    set({
      overallProgress: Math.min(100, Math.round(event.progress * 100)),
      statusMessage: event.message,
      currentPhase: event.phase,
    }),

  clearLogs: () =>
    set({
      currentAgent: null,
      currentPhase: null,
      overallProgress: 0,
      statusMessage: '待機中',
      logs: [],
    }),
}));
