import { useState } from 'react';

interface NSFWDisclaimerProps {
  onConfirm: () => void;
  onDecline: () => void;
}

export function NSFWDisclaimer({ onConfirm, onDecline }: NSFWDisclaimerProps) {
  const [agreed, setAgreed] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-panel max-w-lg w-full mx-4 p-6 rounded-xl">
        <h2 className="text-lg font-bold mb-3">⚠️ NSFWコンテンツに関する同意確認</h2>
        <div className="text-xs text-muted-foreground space-y-2 mb-4">
          <p>この機能を有効にすると、成人向けの表現を含むコンテンツが生成される可能性があります。</p>
          <ul className="list-disc list-inside space-y-1">
            <li>18歳未満の方は使用できません。</li>
            <li>生成されるコンテンツは全て自己責任でご利用ください。</li>
            <li>過度な表現を求める場合の強度調整は、後からも行えます。</li>
          </ul>
        </div>

        <label className="flex items-center gap-2 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="rounded"
          />
          <span className="text-xs">上記の内容を理解し、同意します。</span>
        </label>

        <div className="flex gap-3">
          <button
            onClick={onConfirm}
            disabled={!agreed}
            className="flex-1 btn btn-primary disabled:opacity-50"
          >
            同意して有効にする
          </button>
          <button
            onClick={onDecline}
            className="flex-1 btn btn-secondary"
          >
            同意せず戻る
          </button>
        </div>
      </div>
    </div>
  );
}