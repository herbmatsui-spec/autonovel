import { useState, useEffect } from 'react';
import { planGeneration, getPlanningOptions } from '@/api';
import type { PlanGenerationParams, PlanningOptions } from '@/types/api';
import { useWritingStore } from '@/store/useWritingStore';
import { toast } from 'sonner';

interface PlanningTabProps {
  selectedBook: { id: number; title: string } | null;
  handlePlanGeneration: () => void;
}

export function PlanningTab({ selectedBook, handlePlanGeneration }: PlanningTabProps) {
  const [options, setOptions] = useState<PlanningOptions | null>(null);
  const { wordCount, setWordCount } = useWritingStore();

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
    getPlanningOptions().then(data => {
      setOptions(data);
      if (data.story_archetypes.length > 0) setArchetype(data.story_archetypes[0]);
    }).catch(err => {
      console.error('Failed to load planning options:', err);
      toast.error('オプションの読み込みに失敗しました');
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBook) {
      toast.warning('最初に作品を選択してください。');
      return;
    }
    try {
      setIsSubmitting(true);
      const params: PlanGenerationParams = {
        api_key: '',
        config: {},
        params: {
          genre,
          archetype,
          keywords,
          style_key: styleKey,
          target_eps: targetEps,
          initial_limit: initialLimit,
          cheat_scale: cheatScale,
          system_assist: systemAssist,
          cost_severity: costSeverity,
          word_count: wordCount,
        },
      };
      await planGeneration(params);
      toast.success('企画生成を開始しました。');
      handlePlanGeneration();
    } catch (err: any) {
      toast.error('企画生成に失敗しました: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div>
        <h3 className="text-[1.2rem] text-white font-bold">📋 企画立案</h3>
        <p className="text-[0.85rem] text-secondary">
          小説の基本設定を入力して、AIによる企画案を生成します。
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-panel p-6 flex flex-col gap-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs mb-1 text-secondary">ジャンル</label>
            <select value={genre} onChange={(e) => setGenre(e.target.value)} className="w-full">
              <option value="ファンタジー">ファンタジー</option>
              <option value="ロマンス">ロマンス</option>
              <option value="ミステリー">ミステリー</option>
              <option value="ホラー">ホラー</option>
              <option value="SF">SF</option>
              <option value="官能/ロマンス">官能/ロマンス</option>
              <option value="現代">現代</option>
              <option value="歴史">歴史</option>
              <option value="その他">その他</option>
            </select>
          </div>
          <div>
            <label className="block text-xs mb-1 text-secondary">アーキタイプ (物語の型)</label>
            <select value={archetype} onChange={(e) => setArchetype(e.target.value)} className="w-full">
              {options?.story_archetypes.map(arch => (
                <option key={arch} value={arch}>{arch}</option>
              ))}
              {!options && <option value={archetype}>{archetype}</option>}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs mb-1 text-secondary">文体スタイル</label>
          <select value={styleKey} onChange={(e) => setStyleKey(e.target.value)} className="w-full">
            {options ? (
              Object.entries(options.style_definitions).map(([key, val]) => (
                <option key={key} value={key}>{val.name}</option>
              ))
            ) : (
              <option value="style_web_standard">Web標準</option>
            )}
          </select>
          {options && options.style_definitions[styleKey] && (
            <p className="text-[0.7rem] text-muted-foreground mt-1">
              {options.style_definitions[styleKey].description}
            </p>
          )}
        </div>

        <div>
          <label className="block text-xs mb-1 text-secondary">キーワード（カンマ区切り）</label>
          <input
            type="text"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            className="w-full"
            placeholder="例: 追放, チート, ざまぁ"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs mb-1 text-secondary">目標文字数/話</label>
            <input type="number" value={wordCount} onChange={(e) => setWordCount(Number(e.target.value))} min={1000} max={5000} step={100} className="w-full" />
          </div>
          <div>
            <label className="block text-xs mb-1 text-secondary">目標話数</label>
            <input type="number" value={targetEps} onChange={(e) => setTargetEps(Number(e.target.value))} min={10} max={200} className="w-full" />
          </div>
          <div>
            <label className="block text-xs mb-1 text-secondary">初期プロット数</label>
            <input type="number" value={initialLimit} onChange={(e) => setInitialLimit(Number(e.target.value))} min={1} max={50} className="w-full" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs mb-1 text-secondary">チート強度</label>
            <input type="number" value={cheatScale} onChange={(e) => setCheatScale(Number(e.target.value))} min={0} max={5} className="w-full" />
          </div>
          <div>
            <label className="block text-xs mb-1 text-secondary">システム支援率 (%)</label>
            <input type="number" value={systemAssist} onChange={(e) => setSystemAssist(Number(e.target.value))} min={0} max={100} className="w-full" />
          </div>
          <div>
            <label className="block text-xs mb-1 text-secondary">コスト厳格度</label>
            <input type="number" value={costSeverity} onChange={(e) => setCostSeverity(Number(e.target.value))} min={1} max={5} className="w-full" />
          </div>
        </div>

        <button type="submit" className="btn btn-primary" disabled={isSubmitting || !selectedBook}>
          🚀 企画生成開始
        </button>
      </form>
    </div>
  );
}

