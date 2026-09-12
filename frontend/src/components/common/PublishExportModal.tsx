import React, { useState, useEffect } from 'react';
import { fetchPublishPreview, downloadPublishZip, PublishPreviewResponse } from '../../api/publishing';

interface PublishExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  bookId: number;
  currentChapter?: number;
  branchId?: number;
}

const PLATFORMS = [
  { id: 'narou', name: '小説家になろう' },
  { id: 'kakuyomu', name: 'カクヨム' },
  { id: 'alphapolis', name: 'アルファポリス' },
  { id: 'aozora', name: '青空文庫形式' },
  { id: 'kdp_epub', name: 'Amazon KDP' },
];

export const PublishExportModal: React.FC<PublishExportModalProps> = ({
  isOpen,
  onClose,
  bookId,
  currentChapter = 1,
  branchId,
}) => {
  const [selectedPlatform, setSelectedPlatform] = useState<string>('narou');
  const [previewData, setPreviewData] = useState<PublishPreviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [downloading, setDownloading] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !bookId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);
    setCopied(false);

    fetchPublishPreview(selectedPlatform, bookId, currentChapter, branchId)
      .then((data) => {
        if (isMounted) setPreviewData(data);
      })
      .catch((err) => {
        if (isMounted) setError(err.message || 'プレビューの読み込みに失敗しました');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, bookId, selectedPlatform, currentChapter, branchId]);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (!previewData?.formatted_content) return;
    navigator.clipboard.writeText(previewData.formatted_content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = async () => {
    try {
      setDownloading(true);
      await downloadPublishZip(selectedPlatform, bookId, branchId);
    } catch (err: any) {
      setError(err.message || 'ダウンロードに失敗しました');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-3xl flex flex-col max-h-[90vh] shadow-2xl overflow-hidden text-slate-100 animate-fadeIn">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Web小説投稿サイト向け出力</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              各投稿サイトのルビ・傍点記法およびタイポグラフィ（インデント・空行・三点リーダー）に自動最適化
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Platform Tabs */}
        <div className="flex border-b border-slate-800 px-6 bg-slate-950/40 gap-2 pt-2">
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedPlatform(p.id)}
              className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors ${
                selectedPlatform === p.id
                  ? 'bg-slate-800 text-indigo-400 border-t-2 border-indigo-500 shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>

        {/* Warnings Banner */}
        {previewData?.warnings && previewData.warnings.length > 0 && (
          <div className="mx-6 mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex flex-col gap-1">
            <span className="text-xs font-bold text-amber-400 flex items-center gap-1">
              ⚠️ プラットフォーム投稿規定に関する注意
            </span>
            {previewData.warnings.map((w, idx) => (
              <p key={idx} className="text-xs text-amber-300 pl-4 list-item">
                {w}
              </p>
            ))}
          </div>
        )}

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs">フォーマット変換中...</span>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
              {error}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-semibold text-slate-300">
                  第{previewData?.chapter_number}話: {previewData?.title}（プレビュー）
                </span>
                <span>{previewData?.formatted_content.length ?? 0} 文字</span>
              </div>
              <textarea
                readOnly
                value={previewData?.formatted_content || ''}
                className="w-full h-80 bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-200 resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500 leading-relaxed"
              />
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-950/60">
          <button
            onClick={handleDownload}
            disabled={downloading || loading}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-2 transition-all disabled:opacity-50"
          >
            {downloading ? 'ZIP生成中...' : '📦 全話一括ZIPダウンロード'}
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={handleCopy}
              disabled={loading || !previewData}
              className={`px-5 py-2 text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-2 ${
                copied
                  ? 'bg-emerald-600 text-white'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white'
              }`}
            >
              {copied ? '✓ クリップボードにコピーしました' : '📋 本文をコピー'}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition-colors"
            >
              閉じる
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
