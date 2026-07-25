import React from "react";
import { DigestResponse } from "../../types/easyMode";

interface DigestViewProps {
  digest: DigestResponse;
  onFullGenerate: () => void;
  onPromote: () => void;
  isPromoting: boolean;
}

export const DigestView: React.FC<DigestViewProps> = ({
  digest,
  onFullGenerate,
  onPromote,
  isPromoting,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded bg-teal-500/10 text-teal-400 border border-teal-500/30">
            ファスト・ダイジェスト生成完了
          </span>
          <h2 className="text-2xl font-extrabold text-white mt-1">
            {digest.title}
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onPromote}
            disabled={isPromoting}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold rounded-lg text-sm transition flex items-center gap-2"
          >
            {isPromoting ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <span>🛠️ プロデューサー昇格（上級者モードへ）</span>
            )}
          </button>
          <button
            onClick={onFullGenerate}
            className="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold rounded-lg text-sm shadow-md transition flex items-center gap-1.5"
          >
            <span>📚 残り全話を自動執筆</span>
          </button>
        </div>
      </div>

      {/* Synopsis */}
      <div className="space-y-2">
        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
          📖 全体あらすじ・プロット構想
        </h3>
        <div className="bg-slate-950 p-4 rounded-xl text-slate-300 text-sm whitespace-pre-wrap border border-slate-800">
          {digest.synopsis}
        </div>
      </div>

      {/* Episode 1 & Climax Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Ep 1 */}
        <div className="space-y-2">
          <h3 className="text-sm font-bold text-purple-400 flex items-center gap-1.5">
            <span>第1話 冒頭プレビュー</span>
          </h3>
          <div className="bg-slate-950 p-4 rounded-xl text-slate-300 text-xs leading-relaxed max-h-80 overflow-y-auto whitespace-pre-wrap border border-slate-800">
            {digest.episode_1_text}
          </div>
        </div>

        {/* Climax */}
        <div className="space-y-2">
          <h3 className="text-sm font-bold text-amber-400 flex items-center gap-1.5">
            <span>🔥 見せ場・クライマックス先読み</span>
          </h3>
          <div className="bg-slate-950 p-4 rounded-xl text-slate-300 text-xs leading-relaxed max-h-80 overflow-y-auto whitespace-pre-wrap border border-amber-500/20">
            {digest.climax_preview_text}
          </div>
        </div>
      </div>
    </div>
  );
};
