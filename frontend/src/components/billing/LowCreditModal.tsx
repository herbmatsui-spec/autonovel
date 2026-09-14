import React from 'react';

// LowCreditModal クレジット不足時に自動ポップアップするチャージ案内モーダル
const LowCreditModal: React.FC<{ 
  isOpen: boolean; 
  onClose: () => void;
  requiredCredits: number;
  currentBalance: number;
}> = ({ isOpen, onClose, requiredCredits, currentBalance }) => {
  if (!isOpen) {
    return null;
  }

  const creditsNeeded = requiredCredits - currentBalance;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-bold text-red-400">クレジットが不足しています</h2>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            ×
          </button>
        </div>
        
        <div className="text-center mb-6">
          <div className="text-2xl font-bold text-white mb-4">
            {currentBalance} / {requiredCredits} pt
          </div>
          <p className="text-gray-300 mb-4">
            この操作を実行するにはさらに{creditsNeeded}ptのクレジットが必要です
          </p>
          
          <div className="flex flex-col space-y-3">
            <button 
              onClick={() => {
                // TODO: 実際の実装ではプラン選択モーダルまたは直接チャージフローを開始する
                alert('チャージフローを開始します。実装中です。');
                onClose();
              }}
              className="w-full bg-yellow-500 text-gray-800 font-bold py-2 px-4 rounded hover:bg-yellow-400"
            >
              クレジットをチャージする
            </button>
            
            <button 
              onClick={onClose}
              className="w-full bg-gray-700 text-gray-300 py-2 px-4 rounded hover:bg-gray-600"
            >
              後で行う
            </button>
          </div>
        </div>
        
        <div className="text-center text-gray-400 text-xs mt-4">
          ヒント: プランにアップグレードすると毎月自動的にクレジットが追加されます
        </div>
      </div>
    </div>
  );
};

export default LowCreditModal;