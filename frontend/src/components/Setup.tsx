import React, { useState } from 'react';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

export default function Setup() {
  const { setApiKey } = useUserSettingsStore();
  const navigate = useNavigate();
  const [apiKey, setApiKeyLocal] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || apiKey.length < 10) {
      toast.error('有効なAPIキーを入力してください。');
      return;
    }
    setApiKey(apiKey.trim());
    toast.success('APIキーを設定しました。ホームに戻ります。');
    navigate('/');
  };

  return (
    <div className="min-h-[100vh] bg-[var(--bg-main)] flex items-center justify-center p-6">
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-6">
        <h2 className="text-2xl font-bold">APIキーの設定</h2>
        <p className="text-sm text-muted-foreground">
          Google AI Studio で無料のAPIキーを取得してください：
          <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="underline">
            aistudio.google.com/app/apikey
          </a>
        </p>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKeyLocal(e.target.value)}
          placeholder="AIza... (Google AI Studio で取得)"
          className="w-full px-4 py-2 border rounded"
        />
        <button type="submit" className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          設定してホームへ
        </button>
      </form>
    </div>
  );
}