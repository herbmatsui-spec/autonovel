import React from 'react';
import { PublicationScheduleResponse } from '../../types/commercial';
import { PlatformBadge } from '../common/PlatformBadge';

interface PublicationScheduleTableProps {
  schedules: PublicationScheduleResponse[];
  onCancel: (id: number) => void;
  onRunNow: (id: number) => void;
  onError?: (id: number) => void;
  isLoading?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'text-gray-500 bg-gray-100',
  running: 'text-blue-600 bg-blue-100',
  completed: 'text-green-600 bg-green-100',
  failed: 'text-red-600 bg-red-100',
  cancelled: 'text-gray-400 bg-gray-100',
};

/**
 * 予約投稿一覧テーブルコンポーネント
 */
export const PublicationScheduleTable: React.FC<PublicationScheduleTableProps> = ({
  schedules,
  onCancel,
  onRunNow,
  onError,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="flex justify-center p-8 text-gray-500">
        Loading schedules...
      </div>
    );
  }

  if (schedules.length === 0) {
    return (
      <div className="text-center p-8 text-gray-500 border-2 border-dashed rounded-lg">
        No scheduled publications found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Platform</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Episode Range</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Scheduled At</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Status</th>
            <th className="px-4 py-3 text-right font-semibold text-gray-600">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {schedules.map((s) => (
            <tr key={s.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3">
                <PlatformBadge platform={s.platform} />
              </td>
              <td className="px-4 py-3 text-gray-700">
                {s.episode_range[0]} - {s.episode_range[1]}
              </td>
              <td className="px-4 py-3 text-gray-600">
                {new Date(s.scheduled_at).toLocaleString()}
              </td>
              <td className="px-4 py-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status] || 'bg-gray-100 text-gray-600'}`}>
                  {s.status}
                </span>
              </td>
              <td className="px-4 py-3 text-right space-x-2">
                {s.status === 'pending' && (
                  <>
                    <button
                      onClick={() => onRunNow(s.id)}
                      className="text-blue-600 hover:text-blue-800 font-medium transition-colors"
                    >
                      Run Now
                    </button>
                    <button
                      onClick={() => onCancel(s.id)}
                      className="text-red-600 hover:text-red-800 font-medium transition-colors"
                    >
                      Cancel
                    </button>
                  </>
                )}
                {s.status === 'failed' && (
                  <>
                    <button
                      onClick={() => onRunNow(s.id)}
                      className="text-blue-600 hover:text-blue-800 font-medium transition-colors"
                    >
                      Retry
                    </button>
                    {onError && (
                      <button
                        onClick={() => onError(s.id)}
                        className="text-red-600 hover:text-red-800 font-medium transition-colors ml-2"
                      >
                        Error
                      </button>
                    )}
                  </>
                )}
                {s.status === 'completed' || s.status === 'cancelled' ? (
                  <span className="text-gray-400 italic text-xs">No actions available</span>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PublicationScheduleTable;
