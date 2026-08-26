import { useState, useEffect } from 'react';
import { planGeneration, getPlanningOptions } from '@/api';
import type { PlanGenerationParams, PlanningOptions } from '@/types/api';
import { useWritingStore } from '@/store/useWritingStore';
import { toast } from 'sonner';
import { useBookStore } from '@/store/useBookStore';
import { useNavigate } from 'react-router-dom';
import { useBookDetails } from '@/hooks/useBookDetails';
import { Button } from '@/components/ui/button';
import { LoadingState } from '@/components/ui/LoadingState';

export default function PlanningTab() {
  const { selectedBook } = useBookStore();
  const { wordCount, setWordCount } = useWritingStore();
  const navigate = useNavigate();
  const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null);

  const [options, setOptions] = useState<PlanningOptions | null>(null);
  const [genre, setGenre] = useState('ファンタジー');
  const [archetype, setArchetype] = useState('王道ざまぁ（爽快感最大）');
  const [keywords, setKeywords] = useState('追放, チート, ざまぁ');
  const [targetEps, setTargetEps] = useState(50);
  const [initialLimit, setInitialLimit] = useState(25);
  const [styleKey, setStyleKey] = useState('style_web_standard');
  const [cheatScale, setCheatScale] = useState(4);
  const [systemAssist, setSystemAssist] = useState(70);
  const [costSeverity, setCostSeverity] = useState(2);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (selectedBook?.id) {
      getPlanningOptions().then(data => {
        setOptions(data);
        if (data.story_archetypes.length > 0) setArchetype(data.story_archetypes[0]);
        if (data.style_keys.length > 0) setStyleKey(data.style_keys[0]);
      });
    }
  }, [selectedBook?.id]);

  const handleGeneratePlan = async () => {
    if (!selectedBook?.id) return;
    if (!options) {
      toast.error('プラニングオプションの読み込みに失敗しました。');
      return;
    }
    setIsSubmitting(true);
    try {
      const params: PlanGenerationParams = {
        book_id: selectedBook.id,
        target_word_count: wordCount,
        genre,
        archetype,
        keywords,
        target_eps: targetEps,
        initial_limit,
        style_key: styleKey,
        cheat_scale: cheatScale,
        system_assist: systemAssist,
        cost_severity: costSeverity,
      };
      await planGeneration(params);
      // After generation, refetch book details to update plots, etc.
      if (selectedBook.id) {
        await loadBookDetails(selectedBook.id);
      }
      // Navigate to plots tab to see the generated plot
      navigate('/plots');
      toast.success('プランが生成され、プロットタブに遷移しました。');
    } catch (err) {
      console.error(err);
      toast.error('プラン生成に失敗しました。');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  if (!options) {
    return <div className="text-center py-8">プラニングオプションを読み込み中...</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <h2 className="text-xl font-bold">企画立案 - {selectedBook.title}</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-4">
          <h3 className="font-semibold">基本情報</div>
          <div className="space-y-2">
            <label className="text-sm font-medium">ジャンル</label>
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="block w-full px-3 py-2 border rounded"
            >
              {options?.story_genres.map((g: string) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">ストーリーキャラアーキタイプ</label>
            <select
              value={archetype}
              onChange={(e) => setArchetype(e.target.value)}
              className="block w-full px-3 py-2 border rounded"
            >
              {options?.story_archetypes.map((a: string) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">キーワード（カンマ区切り）</label>
            <input
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="block w-full px-3 py-2 border rounded"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">目標文字数</label>
            <input
              type="number"
              value={wordCount}
              onChange={(e) => setWordCount(parseInt(e.target.value) || 0)}
              className="block w-full px-3 py-2 border rounded"
            />
          </div>
        </div>
        <div className="space-y-4">
          <h3 className="font-semibold">詳細設定</div>
          <div className="space-y-2">
            <label className="text-sm font-medium">目標エピソード数</label>
            <input
              type="number"
              value={targetEps}
              onChange={(e) => setTargetEps(parseInt(e.target.value) || 0)}
              className="block w-full px-3 py-2 border rounded"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">初期制限数</label>
            <input
              type="number"
              value={initialLimit}
              onChange={(e) => setInitialLimit(parseInt(e.target.value) || 0)}
              className="block w-full px-3 py-2 border rounded"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">スタイルキー</label>
            <select
              value={styleKey}
              onChange={(e) => setStyleKey(e.target.value)}
              className="block w-full px-3 py-2 border rounded"
            >
              {options?.style_keys.map((k: string) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">チートスケール</label>
            <input
              type="number"
              value={cheatScale}
              onChange={(e) => setCheatScale(parseInt(e.target.value) || 0)}
              className="block w-full px-3 py-2 border rounded"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">システムアシスト (%)</label>
            <input
              type="number"
              value={systemAssist}
              onChange={(e) => setSystemAssist(parseInt(e.target.value) || 0)}
              className="block w-full px-3 py-2 border rounded"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">コスト重症度</label>
            <input
              type="number"
              value={costSeverity}
              onChange={(e) => setCostSeverity(parseInt(e.target.value) || 0)}
              className="block w-full px-3 py-2 border rounded"
            />
          </div>
        </div>
      </div>
      <div className="flex justify-end mt-6">
        <Button
          variant="destructive"
          onClick={handleGeneratePlan}
          disabled={isSubmitting}
        >
          {isSubmitting ? '生成中...' : 'プランを生成'}
        </Button>
      </div>
    </div>
  );
}