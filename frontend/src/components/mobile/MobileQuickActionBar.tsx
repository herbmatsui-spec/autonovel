import React from 'react';

interface MobileQuickActionBarProps {
  onInsertText: (text: string) => void;
  onAiContinue?: () => void;
  onProofread?: () => void;
}

export const MobileQuickActionBar: React.FC<MobileQuickActionBarProps> = ({
  onInsertText,
  onAiContinue,
  onProofread,
}) => {
  const actions = [
    { label: '「」', insert: '「」', cursorOffset: -1 },
    { label: '……', insert: '……' },
    { label: '――', insert: '――' },
    { label: '　全角空', insert: '　' },
    { label: '🤖 続き', action: onAiContinue, isSpecial: true },
    { label: '✨ 校正', action: onProofread, isSpecial: true },
  ];

  return (
    <div className="md:hidden fixed bottom-[var(--mobile-nav-height)] left-0 right-0 z-30 bg-slate-900/95 backdrop-blur-md border-t border-b border-slate-800 px-3 py-1.5 flex items-center gap-1.5 overflow-x-auto shadow-lg">
      {actions.map((act, idx) => (
        <button
          key={idx}
          onClick={() => {
            if (act.action) {
              act.action();
            } else if (act.insert) {
              onInsertText(act.insert);
            }
          }}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap touch-target transition-colors shadow-sm ${
            act.isSpecial
              ? 'bg-indigo-600 hover:bg-indigo-500 text-white font-semibold'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
          }`}
        >
          {act.label}
        </button>
      ))}
    </div>
  );
};
