import React from 'react';

// CreditBalanceBadge ヘッダー右上に現在の残クレジットを表示するコンポーネント
// 例: 🪙 420 pt
const CreditBalanceBadge: React.FC = () => {
  // TODO: 実際の実装では、APIからクレジット残高を取得するフックを使用
  // 現在はプレースホルダー値を使用
  const creditBalance = 420; // プレースホルダー

  return (
    <div className="flex items-center space-x-2 text-sm font-medium">
      <span className="text-yellow-400">🪙</span>
      <span className="text-white">{creditBalance}</span>
      <span className="text-xs text-gray-400">pt</span>
    </div>
  );
};

export default CreditBalanceBadge;