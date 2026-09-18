import React, { useState, useEffect } from 'react';

interface PublishAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTitle?: string;
  initialText?: string;
}

interface FormattedPayload {
  platform: string;
  chapter_title: string;
  foreword: string;
  main_content: string;
  afterword: string;
  char_count: number;
  ai_disclosure_statement: string;
  validation_warnings: string[];
}

export const PublishAssistantModal: React.FC<PublishAssistantModalProps> = ({
  isOpen,
  onClose,
  initialTitle = '',
  initialText = '',
}) => {
  const [platform, setPlatform] = useState<string>('kakuyomu');
  const [title, setTitle] = useState<string>(initialTitle);
  const [rawText, setRawText] = useState<string>(initialText);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<FormattedPayload | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  useEffect(() => {
    if (initialTitle) setTitle(initialTitle);
    if (initialText) setRawText(initialText);
  }, [initialTitle, initialText]);

  useEffect(() => {
    if (!isOpen) return;
    handleFormat();
  }, [isOpen, platform, title, rawText]);

  const handleFormat = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiKey = localStorage.getItem('AUTONOVEL_API_KEY') || 'dev-key';
      const res = await fetch('/api/publishing-assistant/format', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          platform,
          chapter_title: title || '無題のエピソード',
          raw_text: rawText || '【前書き】前話のおさらい\n\n本文テストです。\n\n【後書き】次回予告',
          ai_role: 'assisted',
        }),
      });

      if (!res.ok) {
        throw new Error(`Formatting failed: ${res.statusText}`);
      }

      const data = await res.json();
      setPayload(data);
    } catch (err: any) {
      setError(err.message || '整形処理に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string, fieldName: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldName);
      // Success indication would be handled by the UI feedback
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      // Fallback: textarea にフォーカス・選択
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      setCopiedField(fieldName);
      setTimeout(() => setCopiedField(null), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl flex flex-col max-h-[92vh] shadow-2xl overflow-hidden text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🛡️ 安全投稿アシスタント（クリップボード整形）</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              アカウントBANリスクのある自動投稿を廃止し、各プラットフォーム規約・AI開示義務に完全準拠したワンクリックコピー支援
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Platform Selector Tabs */}
        <div className="flex border-b border-slate-800 px-6 bg-slate-950/50 gap-3 pt-3">
          {[
            { id: 'kakuyomu', name: 'カクヨム' },
            { id: 'narou', name: '小説家になろう' },
            { id: 'alphapolis', name: 'アルファポリス' },
            { id: 'kindle', name: 'Amazon KDP' },
          ].map((p) => (
            <button
              key={p.id}
              onClick={() => setPlatform(p.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-all border-b-2 ${
                platform === p.id
                  ? 'border-indigo-500 text-indigo-400 bg-slate-900'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Input Controls */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">章・話タイトル</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="例: 第1話 冒険の始まり"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">
                総文字数: <span className="text-indigo-400 font-bold">{payload?.char_count || 0}文字</span>
              </label>
              <div className="text-xs text-slate-400 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2.5">
                AI開示文言自動付与・規約バリデーション有効
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">元テキスト入力（生原稿）</label>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              rows={4}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
              placeholder="【前書き】...\n本文...\n【後書き】..."
            />
          </div>

          {/* Validation Warnings */}
          {payload?.validation_warnings && payload.validation_warnings.length > 0 && (
            <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-4">
              <h4 className="text-xs font-bold text-amber-400 mb-2 flex items-center gap-1.5">
                <span>⚠️ 規約事前チェック & 警告</span>
              </h4>
              <ul className="list-disc list-inside space-y-1 text-xs text-amber-200/90">
                {payload.validation_warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Formatted Output Sections with One-Click Copy */}
          {loading ? (
            <div className="text-center py-10 text-slate-400 text-sm">整形・検証中...</div>
          ) : payload ? (
            <div className="space-y-4">
              {/* Title Copy */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 relative group">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-indigo-400">タイトル入力欄用</span>
                  <button
                    onClick={() => copyToClipboard(payload.chapter_title, 'title')}
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-md transition-colors shadow"
                  >
                    {copiedField === 'title' ? '✓ コピー完了！' : '📋 タイトルをコピー'}
                  </button>
                </div>
                <div className="text-sm font-medium text-white bg-slate-900 p-2.5 rounded border border-slate-800">
                  {payload.chapter_title}
                </div>
              </div>

              {/* Foreword Copy */}
              {payload.foreword && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 relative">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-indigo-400">前書き（まえがき）入力欄用</span>
                    <button
                      onClick={() => copyToClipboard(payload.foreword, 'foreword')}
                      className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-md transition-colors shadow"
                    >
                      {copiedField === 'foreword' ? '✓ コピー完了！' : '📋 前書きをコピー'}
                    </button>
                  </div>
                  <pre className="text-xs font-mono text-slate-300 bg-slate-900 p-2.5 rounded border border-slate-800 whitespace-pre-wrap max-h-32 overflow-y-auto">
                    {payload.foreword}
                  </pre>
                </div>
              )}

              {/* Main Content Copy */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 relative">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-indigo-400">本文入力欄用（ルビ変換済み）</span>
                  <button
                    onClick={() => copyToClipboard(payload.main_content, 'main')}
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-md transition-colors shadow"
                  >
                    {copiedField === 'main' ? '✓ コピー完了！' : '📋 本文をコピー'}
                  </button>
                </div>
                <pre className="text-xs font-mono text-slate-300 bg-slate-900 p-3 rounded border border-slate-800 whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {payload.main_content}
                </pre>
              </div>

              {/* Afterword Copy */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 relative">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-indigo-400">後書き・AI開示文言入力欄用</span>
                    <span className="text-[10px] bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded border border-indigo-800">
                      AI開示義務対応
                    </span>
                  </div>
                  <button
                    onClick={() => copyToClipboard(payload.afterword, 'afterword')}
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs rounded-md transition-colors shadow"
                  >
                    {copiedField === 'afterword' ? '✓ コピー完了！' : '📋 後書きをコピー'}
                  </button>
                </div>
                <pre className="text-xs font-mono text-slate-300 bg-slate-900 p-2.5 rounded border border-slate-800 whitespace-pre-wrap max-h-32 overflow-y-auto">
                  {payload.afterword}
                </pre>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950">
          <div className="text-xs text-slate-400">
            💡 各プラットフォームの投稿管理画面を開き、上記ブロックごとにワンクリックで貼り付けてください。
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded-lg transition-colors"
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
};
