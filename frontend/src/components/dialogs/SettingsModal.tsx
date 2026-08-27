import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { toast } from 'sonner';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const {
    apiKey,
    setApiKey,
    modelType,
    setModelType,
    temperature,
    setTemperature,
    isExpertMode,
    setIsExpertMode,
  } = useUserSettingsStore();

  const [localApiKey, setLocalApiKey] = useState(apiKey);
  const [localModelType, setLocalModelType] = useState(modelType);
  const [localTemperature, setLocalTemperature] = useState(temperature);
  const [localIsExpertMode, setLocalIsExpertMode] = useState(isExpertMode);
  const [isContinuityMonitor, setIsContinuityMonitor] = useState(true);
  const [showApiKey, setShowApiKey] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLocalApiKey(apiKey);
      setLocalModelType(modelType);
      setLocalTemperature(temperature);
      setLocalIsExpertMode(isExpertMode);
    }
  }, [isOpen, apiKey, modelType, temperature, isExpertMode]);

  if (!isOpen) return null;

  const handleSave = () => {
    setApiKey(localApiKey.trim());
    setModelType(localModelType);
    setTemperature(localTemperature);
    setIsExpertMode(localIsExpertMode);
    toast.success('設定を保存しました');
    onClose();
  };

  const hasApiKey = localApiKey.trim().length >= 10;

  const content = (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-modal-title"
      className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
      tabIndex={-1}
    >
      <div className="bg-[#11131a] border border-slate-700/60 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-slide-up flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-[#161922]">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚙️</span>
            <h2 id="settings-modal-title" className="text-lg font-bold text-white">
              全体設定
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors text-sm"
            aria-label="閉じる"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-sm text-slate-200">
          {/* Section 1: API Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-white flex items-center gap-1.5">
                <span>🔑 Gemini APIキー</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-normal">必須</span>
              </label>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-400 hover:text-indigo-300 underline flex items-center gap-1"
              >
                無料取得はこちら ↗
              </a>
            </div>
            <div className="relative">
              <Input
                type={showApiKey ? 'text' : 'password'}
                value={localApiKey}
                onChange={(e) => setLocalApiKey(e.target.value)}
                placeholder="AIzaSy... （Google AI Studioのキーを入力）"
                className="w-full bg-[#1a1d27] border-slate-700 text-white pr-20 text-xs font-mono"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-200 px-2 py-1 bg-slate-800 rounded border border-slate-700"
              >
                {showApiKey ? '隠す' : '表示'}
              </button>
            </div>
            <div className="flex items-center justify-between text-xs mt-1">
              <span className={hasApiKey ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
                {hasApiKey ? '✅ APIキーが入力されています' : '⚠️ APIキーが未設定です（生成に必要です）'}
              </span>
              {hasApiKey && (
                <button
                  type="button"
                  onClick={() => {
                    setLocalApiKey('');
                    toast.info('APIキーをクリアしました');
                  }}
                  className="text-slate-400 hover:text-rose-400 transition-colors"
                >
                  クリア
                </button>
              )}
            </div>
          </div>

          <hr className="border-slate-800" />

          {/* Section 2: Model Selection */}
          <div className="space-y-2">
            <label className="font-semibold text-white flex items-center gap-1.5">
              <span>🤖 使用AIモデル</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setLocalModelType('gemini')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  localModelType === 'gemini'
                    ? 'border-indigo-500 bg-indigo-950/40 text-white shadow-sm ring-1 ring-indigo-500'
                    : 'border-slate-800 bg-[#161922] text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="font-bold flex items-center justify-between">
                  <span>Gemini</span>
                  {localModelType === 'gemini' && <span className="text-xs text-indigo-400">● 選択中</span>}
                </div>
                <div className="text-xs text-slate-400 mt-1">Googleの最新モデル（高速・大容量コンテキスト）</div>
              </button>

              <button
                type="button"
                onClick={() => setLocalModelType('openai')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  localModelType === 'openai'
                    ? 'border-indigo-500 bg-indigo-950/40 text-white shadow-sm ring-1 ring-indigo-500'
                    : 'border-slate-800 bg-[#161922] text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="font-bold flex items-center justify-between">
                  <span>OpenAI</span>
                  {localModelType === 'openai' && <span className="text-xs text-indigo-400">● 選択中</span>}
                </div>
                <div className="text-xs text-slate-400 mt-1">GPT-4oシリーズ対応（OpenAIキーが必要）</div>
              </button>
            </div>
          </div>

          <hr className="border-slate-800" />

          {/* Section 3: Creativity & Temperature */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="font-semibold text-white">
                🎲 創造性（Temperature）: <span className="text-indigo-400 font-mono">{localTemperature}</span>
              </label>
              <span className="text-xs text-slate-400">
                {localTemperature < 0.5 ? '堅実・一貫性重視' : localTemperature > 0.8 ? '斬新・アイデア重視' : '標準バランス'}
              </span>
            </div>
            <input
              type="range"
              min="0.1"
              max="1.2"
              step="0.05"
              value={localTemperature}
              onChange={(e) => setLocalTemperature(parseFloat(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
            <div className="flex justify-between text-[0.7rem] text-slate-500 font-mono">
              <span>0.1 (正確)</span>
              <span>0.7 (標準)</span>
              <span>1.2 (創造的)</span>
            </div>
          </div>

          <hr className="border-slate-800" />

          {/* Section 4: Expert Mode */}
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-[#161922] border border-slate-800">
            <div>
              <div className="font-semibold text-white flex items-center gap-2">
                <span>🧠 エキスパートモード</span>
                <span className={`text-[0.65rem] px-2 py-0.5 rounded-full font-mono ${
                  localIsExpertMode ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-400'
                }`}>
                  {localIsExpertMode ? 'ON' : 'OFF'}
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                プロット詳細設計、文体ラボ、品質監査など高度な機能をメニューに常時表示します。
              </div>
            </div>
            <button
              type="button"
              onClick={() => setLocalIsExpertMode(!localIsExpertMode)}
              className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out cursor-pointer ${
                localIsExpertMode ? 'bg-indigo-600' : 'bg-slate-700'
              }`}
            >
              <div
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                  localIsExpertMode ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Section 5: Continuity Monitor (Step 67) */}
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-[#161922] border border-slate-800">
            <div>
              <div className="font-semibold text-white flex items-center gap-2">
                <span>🔍 Continuity Monitor</span>
                <span className={`text-[0.65rem] px-2 py-0.5 rounded-full font-mono ${
                  isContinuityMonitor ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'
                }`}>
                  {isContinuityMonitor ? 'ON' : 'OFF'}
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                戦闘・会話・探索シーンの連続性と設定整合性をリアルタイムで自動監視します。
              </div>
            </div>
            <button
              type="button"
              id="continuity-monitor-toggle"
              aria-label="Continuity Monitor"
              onClick={() => setIsContinuityMonitor(!isContinuityMonitor)}
              className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out cursor-pointer ${
                isContinuityMonitor ? 'bg-emerald-600' : 'bg-slate-700'
              }`}
            >
              <div
                className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                  isContinuityMonitor ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-[#161922] flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} className="text-slate-300 hover:text-white">
            キャンセル
          </Button>
          <Button
            variant="default"
            onClick={handleSave}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-5"
          >
            設定を保存
          </Button>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}
