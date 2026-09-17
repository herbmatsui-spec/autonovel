import React, { useState } from 'react';

interface CopyButtonProps {
  title: string;
  body: string;
}

export const PlatformCopyButton: React.FC<CopyButtonProps> = ({ title, body }) => {
  const [copiedPlatform, setCopiedPlatform] = useState<string | null>(null);

  const handleCopy = async (platform: 'narou' | 'kakuyomu' | 'alphapolis') => {
    try {
      const resp = await fetch('/api/export/copy/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body, platform }),
      });
      if (!resp.ok) throw new Error('Format failed');
      const data = await resp.json();
      await navigator.clipboard.writeText(data.body);
      setCopiedPlatform(platform);
      setTimeout(() => setCopiedPlatform(null), 2000);
    } catch (err) {
      console.error(err);
      // フォールバック: そのままコピー
      await navigator.clipboard.writeText(body);
      setCopiedPlatform('raw');
      setTimeout(() => setCopiedPlatform(null), 2000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400">整形コピー:</span>
      <button
        onClick={() => handleCopy('narou')}
        className="px-2.5 py-1 text-xs bg-slate-700 hover:bg-sky-600 rounded text-white transition-colors"
      >
        {copiedPlatform === 'narou' ? '✓ コピー済' : 'なろう'}
      </button>
      <button
        onClick={() => handleCopy('kakuyomu')}
        className="px-2.5 py-1 text-xs bg-slate-700 hover:bg-emerald-600 rounded text-white transition-colors"
      >
        {copiedPlatform === 'kakuyomu' ? '✓ コピー済' : 'カクヨム'}
      </button>
      <button
        onClick={() => handleCopy('alphapolis')}
        className="px-2.5 py-1 text-xs bg-slate-700 hover:bg-amber-600 rounded text-white transition-colors"
      >
        {copiedPlatform === 'alphapolis' ? '✓ コピー済' : 'アルファ'}
      </button>
    </div>
  );
};