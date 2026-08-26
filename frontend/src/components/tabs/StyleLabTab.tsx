import { useState } from 'react';
import React from 'react';
import { analyzeStyleDna } from '@/api';
import { toast } from 'sonner';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { StyleDnaResult } from '@/types';

export function StyleLabTab(): React.ReactElement {
  const apiKey = useUserSettingsStore((s) => s.apiKey);
  const [sample, setSample] = useState('');
  const [result, setResult] = useState<StyleDnaResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    if (!sample.trim()) {
      toast.warning('分析用のテキストを入力してください。');
      return;
    }
    if (!apiKey || apiKey.length < 10) {
      toast.warning('有効なAPIキーを入力してください。');
      return;
    }
    try {
      setLoading(true);
      const dna = await analyzeStyleDna(sample);
      setResult(dna);
      toast.success('文体分析が完了しました。');
    } catch (err: unknown) {
      toast.error('分析に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div>
        <h3 className="text-xl text-white font-bold">🧬 文体ラボ</h3>
        <p className="text-secondary text-sm">
          文章のスタイルDNAを解析し、文体の特徴を可視化します。
        </p>
      </div>

      <div className="glass-panel p-6">
        <label htmlFor="stylelab-sample" className="block text-sm font-semibold mb-2">分析用サンプル</label>
        <textarea
          id="stylelab-sample"
          rows={8}
          value={sample}
          onChange={(e) => setSample(e.target.value)}
          className="w-full p-3 text-sm rounded bg-background border border-border resize-y"
          placeholder="分析したい文章をここに貼り付け..."
        />
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="btn btn-primary mt-4"
        >
          {loading ? '分析中...' : '🔬 分析開始'}
        </button>
      </div>

      {result && (
        <div className="glass-panel p-6">
          <h4 className="text-sm font-bold mb-3">📊 分析結果</h4>
          <pre className="text-xs whitespace-pre-wrap bg-background p-4 rounded border border-border">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}