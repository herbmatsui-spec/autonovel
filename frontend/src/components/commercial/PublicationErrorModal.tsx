import React from 'react';

interface PublicationErrorModalProps {
  isOpen: boolean;
  onClose: () => void;
  errorMessage: string;
  scheduleId: number;
}

/**
 * 投稿エラー詳細表示モーダル
 */
export const PublicationErrorModal: React.FC<PublicationErrorModalProps> = ({
  isOpen,
  onClose,
  errorMessage,
  scheduleId,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-red-50">
          <div className="flex items-center space-x-2 text-red-700">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-//9a1 1 0 00-1 1v4a1 1 0 102 0v-4a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <h3 className="text-lg font-bold">投稿エラー詳細</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <div className="mb-4 text-sm text-gray-500">
            Schedule ID: <span className="font-mono font-medium text-gray-700">{scheduleId}</span>
          </div>
          
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 font-mono text-sm text-gray-800 whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
            {errorMessage || 'No error message provided.'}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors font-medium"
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
};

export default PublicationErrorModal;
