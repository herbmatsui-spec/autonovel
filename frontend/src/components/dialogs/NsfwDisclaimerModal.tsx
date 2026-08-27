import { createPortal } from 'react-dom';

interface Props {
  isOpen: boolean;
  onAccept: () => void;
  onCancel: () => void;
}

export function NsfwDisclaimerModal({ isOpen, onAccept, onCancel }: Props) {
  if (!isOpen) return null;

  const content = (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="bg-[#11131a] border border-slate-700/60 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-slide-up flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-[#161922]">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚠️</span>
            <h2 className="text-lg font-bold text-white">NSFWコンテンツに関する同意確認</h2>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors text-sm"
            aria-label="閉じる"
          >✕</button>
        </div>
        <div className="p-6 text-sm text-slate-200 overflow-y-auto flex-1">
          <p className="mb-4">このモードでは、成人向けの官能的な描写を含むコンテンツが生成されます。</p>
          <ol className="list-decimal list-inside mb-4">
            <li>年齢制限: 18歳未満の方の利用を禁止します。</li>
            <li>自己責任: 生成される内容はAI自動生成であり、倫理的・法的判断はユーザー自身の責任です。</li>
            <li>表現の強度: 設定により描写の強度が変動します。不快に感じた場合は直ちにNSFWモードをOFFにしてください。</li>
          </ol>
          <p className="mb-4">上記内容に同意し、官能特化型機能を利用しますか？</p>
          <div className="flex justify-center gap-4">
            <button
              onClick={onAccept}
              className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-500"
            >同意して有効にする</button>
            <button
              onClick={onCancel}
              className="px-4 py-2 bg-slate-600 text-white rounded hover:bg-slate-500"
            >同意せず戻る</button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}
