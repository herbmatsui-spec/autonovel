import { useState } from 'react';
import { analyzeStyleDna } from '@/api';
import { toast } from 'sonner';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { StyleDnaResult } from '@/types';
import { Button } from '@/components/ui/button';

export default function StyleLabTab() {
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
    <div className="animate-fade-in flex flex-col gap-6">
      <h2 className="text-xl font-bold">文体ラボ</h2>
      <div className="space-y-4">
        <div className="flex flex-col gap-2">
          <label htmlFor="style-sample-text" className="text-sm font-medium">分析したいテキストを入力</label>
          <textarea
            id="style-sample-text"
            value={sample}
            onChange={(e) => setSample(e.target.value)}
            rows={8}
            className="block w-full px-3 py-2 border rounded"
            placeholder="ここで文体を分析したいテキストを貼り付けてください..."
          />
        </div>
        <div className="flex justify-end">
          <Button
            variant="default"
            onClick={handleAnalyze}
            disabled={loading}
          >
            {loading ? '分析中...' : '文体を分析'}
          </Button>
        </div>
      </div>
      {result && (
        <div className="border rounded-lg p-4 mt-6">
          <h3 className="font-semibold mb-2">分析結果</h3>
          <pre className="text-xs bg-[var(--muted)] p-3 rounded overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}