import React, { useState, useEffect, useCallback } from 'react';
import { 
  getPublicationSchedules, 
  createPublicationSchedule, 
  cancelPublicationSchedule, 
  runPublicationScheduleNow 
} from '../../api/commercial';
import { PublicationScheduleResponse, PublicationScheduleCreate } from '../../types/commercial';
import { PublicationScheduleTable } from './PublicationScheduleTable';
import { PublicationScheduleModal } from './PublicationScheduleModal';
import { PublicationErrorModal } from './PublicationErrorModal';

interface CommercialPublishPanelProps {
  bookId: number;
  onToast?: (msg: string, type: "success" | "error" | "info") => void;
}

/**
 * 商用投稿統合パネル
 * 予約投稿の一覧表示、新規登録、即時実行、キャンセル、エラー詳細確認を統合的に管理する
 */
export const CommercialPublishPanel: React.FC<CommercialPublishPanelProps> = ({ bookId, onToast }) => {
  const [schedules, setSchedules] = useState<PublicationScheduleResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isErrorModalOpen, setIsErrorModalOpen] = useState(false);
  const [selectedError, setSelectedError] = useState<{ id: number; message: string } | null>(null);

  // スケジュール一覧の取得
  const fetchSchedules = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getPublicationSchedules(bookId);
      setSchedules(data);
    } catch (error) {
      console.error("Failed to fetch publication schedules:", error);
      // 必要に応じてトースト通知などを追加
    } finally {
      setIsLoading(false);
    }
  }, [bookId]);

  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  // 投稿進行中のステータスを自動更新するためのポーリング設定
  useEffect(() => {
    const hasRunningTask = schedules.some(s => s.status === 'running');
    if (!hasRunningTask) return;

    const interval = setInterval(() => {
      fetchSchedules();
    }, 5000); // 5秒ごとに更新

    return () => clearInterval(interval);
  }, [schedules, fetchSchedules]);

  // 新規スケジュール登録
  const handleCreateSchedule = async (data: PublicationScheduleCreate) => {
    try {
      await createPublicationSchedule(data);
      setIsModalOpen(false);
      await fetchSchedules();
      onToast?.("投稿スケジュールを登録しました", "success");
    } catch (error) {
      console.error("Failed to create schedule:", error);
      onToast?.("スケジュールの登録に失敗しました", "error");
    }
  };

  // スケジュールキャンセル
  const handleCancelSchedule = async (id: number) => {
    if (!window.confirm("この予約投稿を取り消しますか？")) return;
    try {
      await cancelPublicationSchedule(id);
      await fetchSchedules();
    } catch (error) {
      console.error("Failed to cancel schedule:", error);
      onToast?.("スケジュールの取り消しに失敗しました", "error");
    }
  };

  // 即時実行 / リトライ
  const handleRunNow = async (id: number) => {
    try {
      await runPublicationScheduleNow(id);
      await fetchSchedules();
    } catch (error) {
      console.error("Failed to run schedule now:", error);
      onToast?.("即時実行に失敗しました", "error");
    }
  };

  // エラー詳細の表示
  const handleShowError = (id: number) => {
    const schedule = schedules.find(s => s.id === id);
    if (schedule && schedule.error_message) {
      setSelectedError({ id, message: schedule.error_message });
      setIsErrorModalOpen(true);
    } else {
      onToast?.("エラーメッセージが見つかりませんでした", "info");
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">商用出版・投稿管理</h2>
          <p className="text-sm text-gray-500">プラットフォームへの予約投稿を管理し、配信スケジュールを制御します。</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>新規予約投稿</span>
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
          <h3 className="font-semibold text-gray-700">投稿スケジュール一覧</h3>
        </div>
        <div className="p-6">
          <PublicationScheduleTable
            schedules={schedules}
            onCancel={handleCancelSchedule}
            onRunNow={handleRunNow}
            onError={handleShowError}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* 新規登録モーダル */}
      <PublicationScheduleModal
        bookId={bookId}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateSchedule}
        isLoading={isLoading}
      />

      {/* エラー詳細モーダル */}
      <PublicationErrorModal
        isOpen={isErrorModalOpen}
        onClose={() => setIsErrorModalOpen(false)}
        scheduleId={selectedError?.id || 0}
        errorMessage={selectedError?.message || ''}
      />
    </div>
  );
};

export default CommercialPublishPanel;
