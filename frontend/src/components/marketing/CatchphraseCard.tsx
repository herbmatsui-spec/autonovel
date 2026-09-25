import React, { useState } from 'react';
import { apiFetch, handleResponse } from '../../api/client';
import { useToast } from '../../hooks/useToast';

/**
 * Step 20: 35文字キャッチコピー候補表示＆ワンクリックコピーUIコンポーネント。
 *
 * 文字数インジケーター（緑: 32文字以内 / 赤: 35文字超）と
 * ワンクリックコピーボタンを備える。
 */

export interface CatchphraseItem {
  catchphrase: string;
  score: number;
  char_count: number;
  type: string;
}

interface CatchphraseCardProps {
  /** 企画設定（ジャンル・コンセプト等のテキスト） */
  projectSettings: string;
  /** 生成する候補数（既定20） */
  candidateCount?: number;
}

const CATCHPHRASE_MAX_LENGTH = 35;
const CATCHPHRASE_OPTIMAL_MAX = 32;

const TYPE_LABELS: Record<string, string> = {
  dialogue: 'セリフ型',
  confession: '衝撃告白型',
  reversal: '地位反転型',
  unknown: 'その他',
};

export const CatchphraseCard: React.FC<CatchphraseCardProps> = ({
  projectSettings,
  candidateCount = 20,
}) => {
  const [candidates, setCandidates] = useState<CatchphraseItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const { addToast } = useToast();

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const resp = await apiFetch('/api/marketing/catchphrases', {
        method: 'POST',
        body: JSON.stringify({
          project_settings: projectSettings,
          candidate_count: candidateCount,
        }),
      });
      const data = await handleResponse<CatchphraseItem[]>(resp);
      setCandidates(Array.isArray(data) ? data : []);
      addToast(`✨ キャッチコピーを${Array.isArray(data) ? data.length : 0}件生成しました`, 'success');
    } catch (err) {
      console.error(err);
      addToast('⚠️ キャッチコピーの生成に失敗しました', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      addToast('📋 キャッチコピーをコピーしました', 'success');
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error(err);
      addToast('⚠️ コピーに失敗しました', 'error');
    }
  };

  /** 文字数インジケーターの色クラス（緑: 32文字以内 / 赤: 35文字超） */
  const charCountColor = (count: number): string => {
    if (count > CATCHPHRASE_MAX_LENGTH) return 'text-red-400';
    if (count <= CATCHPHRASE_OPTIMAL_MAX) return 'text-emerald-400';
    return 'text-amber-400';
  };

  return (
    <div className="space-y-3" data-testid="catchphrase-card">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">
          ✨ カクヨム用35文字キャッチコピー
        </h3>
        <button
          onClick={handleGenerate}
          disabled={loading || !projectSettings}
          className="px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 rounded text-white transition-colors"
          data-testid="catchphrase-generate-button"
        >
          {loading ? '生成中...' : 'キャッチコピー生成'}
        </button>
      </div>

      {candidates.length === 0 && !loading && (
        <p className="text-xs text-slate-500">
          企画設定からカクヨムで最も目立つ35文字キャッチコピーを生成します。
        </p>
      )}

      <div className="space-y-2">
        {candidates.map((item, index) => (
          <div
            key={`${item.catchphrase}-${index}`}
            className="flex items-start justify-between gap-2 p-2.5 bg-slate-800/60 border border-slate-700 rounded"
            data-testid={`catchphrase-item-${index}`}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-100 break-words">{item.catchphrase}</p>
              <div className="flex items-center gap-2 mt-1">
                {/* Step 20: 文字数インジケーター */}
                <span
                  className={`text-[10px] font-mono ${charCountColor(item.char_count)}`}
                  data-testid={`catchphrase-char-count-${index}`}
                >
                  {item.char_count}/{CATCHPHRASE_MAX_LENGTH}字
                </span>
                <span className="text-[10px] text-slate-500">
                  {TYPE_LABELS[item.type] ?? TYPE_LABELS.unknown}
                </span>
                <span className="text-[10px] text-sky-400">CTR Score: {Math.round(item.score)}</span>
              </div>
            </div>
            <button
              onClick={() => handleCopy(item.catchphrase, index)}
              className={`px-2 py-1 text-xs shrink-0 rounded transition-colors ${
                copiedIndex === index
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-700 hover:bg-slate-600 text-slate-200'
              }`}
              data-testid={`catchphrase-copy-button-${index}`}
            >
              {copiedIndex === index ? '✓ コピー済' : 'コピー'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CatchphraseCard;
