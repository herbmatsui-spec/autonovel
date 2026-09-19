import React, { useState } from 'react';
import { apiFetch, handleResponse } from '../../api/client';
import { useToast } from '../../hooks/useToast';

interface FormattedResponse {
  title: string;
  foreword: string;
  body: string;
  afterword: string;
  total_characters: number;
  platform: string;
}

interface CopyButtonProps {
  title: string;
  body: string;
}

export const PlatformCopyButton: React.FC<CopyButtonProps> = ({ title, body }) => {
  const [copiedPlatform, setCopiedPlatform] = useState<string | null>(null);
  // Step 19: 字下げON/OFFトグル（なろう推奨: ON / カクヨム推奨: OFF）
  const [indentEnabled, setIndentEnabled] = useState<boolean>(true);
  const { addToast } = useToast();

  const handleToggleIndent = () => {
    setIndentEnabled((prev) => {
      const next = !prev;
      addToast(
        next
          ? '📐 全角字下げ: ON（なろう推奨）'
          : '📐 字下げなし: OFF（カクヨム推奨）',
        'info',
      );
      return next;
    });
  };

  const handleCopy = async (platform: 'narou' | 'kakuyomu' | 'alphapolis') => {
    try {
      const resp = await apiFetch('/api/export/copy/', {
        method: 'POST',
        // Step 19: indent_enabled をAPIリクエストに含める
        body: JSON.stringify({ title, body, platform, indent_enabled: indentEnabled }),
      });
      const data = await handleResponse<FormattedResponse>(resp);
      await navigator.clipboard.writeText(data.body);
      setCopiedPlatform(platform);
      addToast(`✨ ${platform === 'narou' ? 'なろう' : platform === 'kakuyomu' ? 'カクヨム' : 'アルファポリス'}形式でコピーしました`, 'success');
      setTimeout(() => setCopiedPlatform(null), 2000);
    } catch (err) {
      console.error(err);
      // フォールバック: そのままコピー
      await navigator.clipboard.writeText(body);
      setCopiedPlatform('raw');
      addToast('⚠️ 整形に失敗しました。生テキストをコピーしました。', 'error');
      setTimeout(() => setCopiedPlatform(null), 2000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400">整形コピー:</span>
      {/* Step 19: 字下げON/OFF切り替えトグルスイッチ */}
      <label
        className="flex items-center gap-1.5 cursor-pointer select-none"
        title="全角字下げ（なろう推奨）と字下げなし（カクヨム推奨）を切り替え"
      >
        <input
          type="checkbox"
          checked={indentEnabled}
          onChange={handleToggleIndent}
          className="sr-only"
          data-testid="indent-toggle"
        />
        <span
          className={`relative inline-block w-8 h-4 rounded-full transition-colors ${
            indentEnabled ? 'bg-sky-600' : 'bg-slate-600'
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${
              indentEnabled ? 'translate-x-4' : ''
            }`}
          />
        </span>
        <span className="text-xs text-slate-300">
          {indentEnabled ? '字下げON' : '字下げOFF'}
        </span>
      </label>
      <button
        onClick={() => handleCopy('narou')}
        className={`px-2.5 py-1 text-xs bg-slate-700 hover:bg-sky-600 rounded text-white transition-colors ${
          copiedPlatform === 'narou' ? 'animate-pulse ring-2 ring-sky-400' : ''
        }`}
      >
        {copiedPlatform === 'narou' ? '✓ コピー済' : 'なろう'}
      </button>
      <button
        onClick={() => handleCopy('kakuyomu')}
        className={`px-2.5 py-1 text-xs bg-slate-700 hover:bg-emerald-600 rounded text-white transition-colors ${
          copiedPlatform === 'kakuyomu' ? 'animate-pulse ring-2 ring-emerald-400' : ''
        }`}
      >
        {copiedPlatform === 'kakuyomu' ? '✓ コピー済' : 'カクヨム'}
      </button>
      <button
        onClick={() => handleCopy('alphapolis')}
        className={`px-2.5 py-1 text-xs bg-slate-700 hover:bg-amber-600 rounded text-white transition-colors ${
          copiedPlatform === 'alphapolis' ? 'animate-pulse ring-2 ring-amber-400' : ''
        }`}
      >
        {copiedPlatform === 'alphapolis' ? '✓ コピー済' : 'アルファ'}
      </button>
    </div>
  );
};
