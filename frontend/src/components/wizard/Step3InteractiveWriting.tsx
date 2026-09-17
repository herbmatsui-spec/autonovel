import React, { useState } from 'react';
import { PlatformCopyButton } from '../common/PlatformCopyButton';

interface Step3Props {
  currentEpisode: number;
  chapterTitle: string;
  chapterContent: string;
  isGenerating: boolean;
  onGenerateNext: () => void;
  onRegenerate: () => void;
}

export const Step3InteractiveWriting: React.FC<Step3Props> = ({
  currentEpisode,
  chapterTitle,
  chapterContent,
  isGenerating,
  onGenerateNext,
  onRegenerate,
}) => {
  return (
    <div className="wizard-step step3-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-amber-400">
          第{currentEpisode}話: {chapterTitle}
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

      <div className="flex gap-4">
        <button
          onClick={onRegenerate}
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