import React from 'react';

export interface OutlineItem {
  episode: number;
  title: string;
  outline: string;
  cliffhangerType?: 'New Crisis' | 'Shocking Truth' | 'Quiet Foreshadowing';
  sensoryFocus?: string[];
  foreshadowingNotes?: string;
}

interface Step2Props {
  outlines: OutlineItem[];
  onBack: () => void;
  onConfirm: () => void;
}

export const Step2StructureReview: React.FC<Step2Props> = ({ outlines, onBack, onConfirm }) => {
  return (
    <div className="wizard-step step2-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold mb-2 text-emerald-400">Step 2: 全章構成と五感ビート・引きの確認</h2>
      <p className="text-slate-400 mb-6 text-sm">
        読者の離脱を防ぐ「クリフハンガー3分類」と「五感タグ配分」です。確認して執筆へ進みましょう。
      </p>

      <div className="space-y-3 max-h-96 overflow-y-auto pr-2 mb-6">
        {outlines.map((item) => (
          <div key={item.episode} className="p-3.5 bg-slate-800 border border-slate-700 rounded-lg flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-sky-300">第{item.episode}話: {item.title}</span>
              <div className="flex gap-2 items-center">
                {item.cliffhangerType && (
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                    item.cliffhangerType === 'Shocking Truth' ? 'bg-red-900 text-red-200 border border-red-700' :
                    item.cliffhangerType === 'New Crisis' ? 'bg-amber-900 text-amber-200 border border-amber-700' :
                    'bg-purple-900 text-purple-200 border border-purple-700'
                  }`}>
                    引き: {item.cliffhangerType}
                  </span>
                )}
                {item.foreshadowingNotes && (
                  <span className="text-xs px-2 py-0.5 bg-sky-900 text-sky-200 rounded border border-sky-700">
                    伏線: {item.foreshadowingNotes}
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm text-slate-300">{item.outline}</p>
            {item.sensoryFocus && item.sensoryFocus.length > 0 && (
              <div className="text-xs text-slate-400 flex gap-2">
                <span>五感描写:</span>
                {item.sensoryFocus.map((s) => (
                  <span key={s} className="text-emerald-400">#{s}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-4">
        <button
          onClick={onBack}
          className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded font-semibold transition-colors"
        >
          ← 戻ってプロットを修正
        </button>
        <button
          onClick={onConfirm}
          className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 rounded font-semibold transition-colors"
        >
          構成を確定して執筆を開始する →
        </button>
      </div>
    </div>
  );
};