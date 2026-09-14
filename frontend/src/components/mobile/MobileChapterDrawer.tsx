import React from 'react';

interface ChapterItem {
  id?: number;
  ep_num: number;
  title: string;
  status?: string;
}

interface MobileChapterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  chapters: ChapterItem[];
  currentChapterId?: number;
  onSelectChapter: (chapterId: number) => void;
}

export const MobileChapterDrawer: React.FC<MobileChapterDrawerProps> = ({
  isOpen,
  onClose,
  chapters,
  currentChapterId,
  onSelectChapter,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/60 backdrop-blur-sm md:hidden animate-fadeIn">
      <div className="bg-slate-900 border-t border-slate-700/80 rounded-t-3xl p-6 max-h-[75vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span>📖 エピソード選択ドロワー</span>
          </h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg touch-target"
          >
            ✕
          </button>
        </div>

        <div className="overflow-y-auto space-y-2 py-4 flex-1">
          {chapters.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-xs">エピソードがありません</div>
          ) : (
            chapters.map((ch, idx) => {
              const chapterId = ch.id ?? ch.ep_num ?? (idx + 1);
              const isSelected = chapterId === currentChapterId;
              return (
                <button
                  key={chapterId}
                  onClick={() => {
                    onSelectChapter(chapterId);
                    onClose();
                  }}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all flex items-center justify-between touch-target ${
                    isSelected
                      ? 'bg-indigo-950/60 border-indigo-500 text-white shadow-lg'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/50'
                  }`}
                >
                  <div>
                    <div className="text-xs font-semibold text-indigo-400 mb-0.5">第 {ch.ep_num} 話</div>
                    <div className="text-sm font-medium">{ch.title || '無題のエピソード'}</div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {ch.status || '下書き'}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
