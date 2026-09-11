import React, { useState } from 'react';
import { CommercialPlatform, PublicationScheduleCreate } from '../../types/commercial';

interface PublicationScheduleModalProps {
  bookId: number;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: PublicationScheduleCreate) => Promise<void>;
  isLoading?: boolean;
}

/**
 * 新規予約投稿登録モーダルコンポーネント
 */
export const PublicationScheduleModal: React.FC<PublicationScheduleModalProps> = ({
  bookId,
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}) => {
  const [platform, setPlatform] = useState<CommercialPlatform>('narou');
  const [rangeStart, setRangeStart] = useState<number>(1);
  const [rangeEnd, setRangeEnd] = useState<number>(1);
  const [scheduledAt, setScheduledAt] = useState<string>(
    new Date(Date.now() + 3600000).toISOString().slice(0, 16) // 1 hour from now, local format
  );

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      book_id: bookId,
      platform,
      episode_range: [rangeStart, rangeEnd],
      scheduled_at: scheduledAt,
    });
  };

  // In a real implementation, we'd use a form library or a submit handler prop.
  // To keep it simple and consistent with the plan, I'll implement the UI here 
  // and the logic will be integrated into the CommercialPublishPanel.

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h3 className="text-lg font-bold text-gray-800">新規予約投稿の作成</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">投稿先プラットフォーム</label>
            <div className="grid grid-cols-2 gap-2">
              {(['narou', 'kakuyomu', 'kindle', 'kobo'] as CommercialPlatform[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPlatform(p)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-all border ${
                    platform === p 
                      ? 'bg-blue-50 border-blue-500 text-blue-700 ring-2 ring-blue-200' 
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {p === 'narou' && '小説家になろう'}
                  {p === 'kakuyomu' && 'カクヨム'}
                  {p === 'kindle' && 'Kindle'}
                  {p === 'kobo' && 'Kobo'}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">投稿話数範囲</label>
            <div className="flex items-center space-x-3">
              <input
                type="number"
                value={rangeStart}
                onChange={(e) => setRangeStart(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                min="1"
              />
              <span className="text-gray-400">〜</span>
              <input
                type="number"
                value={rangeEnd}
                onChange={(e) => setRangeEnd(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                min="1"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">予約日時</label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
            />
          </div>

          <div className="pt-4 flex space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              キャンセル
            </button>
            <button
              type="submit"
              data-testid="submit-button"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300 transition-colors font-medium"
            >
              {isLoading ? '登録中...' : 'スケジュール登録'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PublicationScheduleModal;
