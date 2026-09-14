import React from 'react';

// PricingModal プラン比較カードと「プランをアップグレード」ボタンを表示するモーダル
const PricingModal: React.FC<{ 
  isOpen: boolean; 
  onClose: () => void; 
}> = ({ isOpen, onClose }) => {
  // プラン設定（実際の実装ではAPIまたは設定ファイルから取得）
  const plans = [
    {
      id: 'free',
      name: 'Free',
      price: 0,
      credits: 50,
      popular: false,
      features: [
        'Basic generation',
        '50 credits/month',
        '1 parallel job',
        'Community support'
      ]
    },
    {
      id: 'starter',
      name: 'Starter',
      price: 980,
      credits: 300,
      popular: true,
      features: [
        'Standard generation',
        '300 credits/month',
        '2 parallel jobs',
        'Email support'
      ]
    },
    {
      id: 'pro',
      name: 'Pro',
      price: 2980,
      credits: 1200,
      popular: false,
      features: [
        'Advanced generation',
        '1200 credits/month',
        '4 parallel jobs',
        'Priority support'
      ]
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 9800,
      credits: 5000,
      popular: false,
      features: [
        'Premium generation',
        '5000 credits/month',
        '10 parallel jobs',
        'Dedicated support'
      ]
    }
  ];

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4">
        <div className="flex justify-between items-start mb-6">
          <h2 className="text-xl font-bold text-white">プランを選択</h2>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            ×
          </button>
        </div>
        
        <div className="grid gap-4 mb-6">
          {plans.map(plan => (
            <div 
              key={plan.id}
              className={`border rounded-lg p-4 ${plan.popular ? 'border-yellow-400 bg-gray-700' : 'border-gray-600'}`}
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-white">{plan.name}</h3>
                  {plan.popular && (
                    <span className="inline-block bg-yellow-500 text-gray-800 text-xs px-2 py-1 rounded ml-2">
                      人気
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <span className="block text-2xl font-bold text-white">¥{plan.price}</span>
                  <span className="text-xs text-gray-400">/月</span>
                </div>
              </div>
              
              <div className="flex items-start space-x-3 mb-4">
                <span className="text-yellow-400">🪙</span>
                <span className="text-white">{plan.credits}</span>
                <span className="ml-1 text-xs text-gray-400">クレジット/月</span>
              </div>
              
              <ul className="space-y-2 text-sm text-gray-300">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-yellow-400">✓</span>
                    <span className="ml-2">{feature}</span>
                  </li>
                ))}
              </ul>
              
              <button 
                onClick={() => {
                  // TODO: 実際の実装ではStripeチェックアウトセッションを作成するAPIを呼び出す
                  alert(`プラン "${plan.name}" にアップグレードします。実装中です。`);
                  onClose();
                }}
                className="w-full bg-yellow-500 text-gray-800 font-bold py-2 px-4 rounded hover:bg-yellow-400 disabled:opacity-50"
              >
                プランをアップグレード
              </button>
            </div>
          ))}
        </div>
        
        <div className="text-center text-gray-400 text-sm">
          すべてのプランには月末に未使用のクレジットが繰り越されます
        </div>
      </div>
    </div>
  );
};

export default PricingModal;