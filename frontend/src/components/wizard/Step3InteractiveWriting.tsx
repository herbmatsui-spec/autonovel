import React, { useState, useEffect, useCallback, useRef } from 'react';
import { PlatformCopyButton } from '../common/PlatformCopyButton';
import { StreamingProgressBar } from '../common/StreamingProgressBar';
import { subscribeWritingStreamFetch, WritingStreamEvent } from '../../api/wizard';

interface Step3Props {
  book_id: number;
  ep_num: number;
  branch_id: number;
  chapterTitle: string;
  chapterContent: string;
  isGenerating: boolean;
  onGenerateNext: () => void | Promise<void>;
  onRegenerate: () => void;
}

export const Step3InteractiveWriting: React.FC<Step3Props> = ({
  book_id,
  ep_num,
  branch_id,
  chapterTitle,
  chapterContent,
  isGenerating,
  onGenerateNext,
  onRegenerate,
}) => {
  const [streamProgress, setStreamProgress] = useState(0);
  const [streamPhase, setStreamPhase] = useState<'ContextBuilding' | 'Drafting' | 'Auditing' | 'Complete' | 'Error' | 'Connecting'>('Connecting');
  const [streamStatus, setStreamStatus] = useState<'connecting' | 'connected' | 'receiving' | 'completed' | 'error' | 'disconnected'>('connecting');
  const [streamElapsed, setStreamElapsed] = useState(0);
  const [streamError, setStreamError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // Setup SSE stream subscription with AbortController
    const controller = new AbortController();
    abortControllerRef.current = controller;

    subscribeWritingStreamFetch(
      book_id,
      ep_num,
      branch_id,
      (event: WritingStreamEvent) => {
        setStreamProgress(event.progress);
        setStreamPhase(event.phase);
        setStreamStatus(event.phase === 'Error' ? 'error' : 
                       event.phase === 'Complete' ? 'completed' : 
                       event.progress > 0 ? 'receiving' : 'connected');
        setStreamElapsed(Math.floor(event.timestamp / 1000)); // Assuming timestamp is in seconds
        setStreamError(event.phase === 'Error' ? event.message || 'Unknown error' : null);
      },
      controller.signal
    ).catch((err) => {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      console.error('SSE stream error:', err);
      setStreamStatus('error');
      setStreamError(err instanceof Error ? err.message : 'ストリーム接続に失敗しました');
    });

    // Cleanup on unmount
    return () => {
      controller.abort();
    };
  }, [book_id, ep_num, branch_id]);

  const handleRegenerate = () => {
    onRegenerate();
    // Reset stream state
    setStreamProgress(0);
    setStreamPhase('Connecting');
    setStreamStatus('connecting');
    setStreamElapsed(0);
    setStreamError(null);
  };

  return (
    <div className="wizard-step step3-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-amber-400">
          第{ep_num}話: {chapterTitle}
        </h2>
        <PlatformCopyButton title={chapterTitle} body={chapterContent} />
      </div>

      <div className="relative mb-6">
        <textarea
          rows={16}
          readOnly={isGenerating}
          value={chapterContent}
          className="w-full p-4 rounded bg-slate-950 border border-slate-800 text-slate-100 font-serif leading-relaxed text-base focus:outline-none focus:border-amber-500"
          placeholder={isGenerating ? "AIが本文を執筆中... (約30秒)" : "本文がここに表示されます"}
        />
        {isGenerating && (
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center">
            <span className="text-sky-300 font-semibold animate-pulse">執筆＆二層監査中... ⚡</span>
          </div>
        )}
      </div>

      {/* Streaming Progress Bar */}
      <div className="mb-6">
        <StreamingProgressBar
          progress={streamProgress}
          phaseName={streamPhase}
          elapsedSeconds={streamElapsed}
          connectionStatus={streamStatus}
          onElapsedChange={setStreamElapsed}
        />
        {streamError && (
          <div className="mt-2 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
            エラー: {streamError}
          </div>
        )}
      </div>

      <div className="flex gap-4">
        <button
          onClick={handleRegenerate}
          disabled={isGenerating}
          className="px-6 py-3 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded font-semibold transition-colors"
        >
          リテイク（再執筆）
        </button>
        <button
          onClick={onGenerateNext}
          disabled={isGenerating}
          className="flex-1 py-3 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded font-semibold transition-colors"
        >
          次の一話を執筆する →
        </button>
      </div>
    </div>
  );
};