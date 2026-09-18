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
  const { addToast } = useToast();

  const handleCopy = async (platform: 'narou' | 'kakuyomu' | 'alphapolis') => {
    try {
      const resp = await apiFetch('/api/export/copy/', {
        method: 'POST',
        body: JSON.stringify({ title, body, platform }),
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