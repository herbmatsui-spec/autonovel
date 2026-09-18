import React, { useState } from 'react';
import { expandBeats, ExpandBeatsRequest, BeatItem } from '../../api/wizard';

interface Step1Props {
  onNext: (data: {
    title: string;
    genre: string;
    synopsis: string;
    targetChapters: number;
    cheatScale: number;
    growthCurve: string;
    systemAssist: number;
    costSeverity: number;
    beats: BeatItem[];
  }) => void;
}

export const Step1PlotInput: React.FC<Step1Props> = ({ onNext }) => {
  const [title, setTitle] = useState('');
  const [genre, setGenre] = useState('fantasy');
  const [synopsis, setSynopsis] = useState('');
  const [targetChapters, setTargetChapters] = useState(20);
  const [cheatScale, setCheatScale] = useState(4);
  const [growthCurve, setGrowthCurve] = useState('最初からカンスト(無双)');
  const [systemAssist, setSystemAssist] = useState(70);
  const [costSeverity, setCostSeverity] = useState(2);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateForm = (): boolean => {
    if (!title.trim()) {
      setError('作品タイトルを入力してください');
      return false;
    }
    if (!synopsis.trim()) {
      setError('あらすじ・コアアイデアを入力してください');
      return false;
    }
    if (cheatScale < 1 || cheatScale > 5) {
      setError('チート度は1〜5で設定してください');
      return false;
    }
    if (costSeverity < 1 || costSeverity > 5) {
      setError('代償・世界リスク過酷度は1〜5で設定してください');
      return false;
    }
    if (systemAssist < 0 || systemAssist > 100) {
      setError('システム支援度は0〜100で設定してください');
      return false;
    }
    if (targetChapters < 1 || targetChapters > 100) {
      setError('目標話数は1〜100で設定してください');
      return false;
    }
    setError(null);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsLoading(true);
    setError(null);

    try {
      const request: ExpandBeatsRequest = {
        title,
        genre,
        synopsis,
        target_chapters: targetChapters,
        cheat_scale: cheatScale,
        growth_curve: growthCurve,
        system_assist: systemAssist,
        cost_severity: costSeverity,
      };

      const beats = await expandBeats(request);

      onNext({
        title,
        genre,
        synopsis,
        targetChapters,
        cheatScale,
        growthCurve,
        systemAssist,
        costSeverity,
        beats,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'ビート生成に失敗しました';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="wizard-step step1-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold mb-2 text-sky-400">Step 1: 企画アイデアと成長曲線の設計</h2>
      <p className="text-slate-400 mb-6 text-sm">主人公のチート度や成長曲線、リスク過酷度を設定し、読者を引き込む企画の骨格を作ります。</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium mb-1">作品タイトル</label>
          <input
            type="text"
            className="w-full p-2.5 rounded bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-sky-500"
            placeholder="例: 魔王の娘に転生した鍛冶屋の日常"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">ジャンル</label>
            <select
              className="w-full p-2.5 rounded bg-slate-800 border border-slate-700 text-white"
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              disabled={isLoading}
            >
              <option value="fantasy">異世界ハイファンタジー</option>
              <option value="modern_fantasy">現代ダンジョン・バトル</option>
              <option value="romance">悪役令嬢・恋愛</option>
              <option value="scifi">近未来SF・サイバーパンク</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">成長曲線モデル</label>
            <select
              className="w-full p-2.5 rounded bg-slate-800 border border-slate-700 text-white"
              value={growthCurve}
              onChange={(e) => setGrowthCurve(e.target.value)}
              disabled={isLoading}
            >
              <option value="最初からカンスト(無双)">最初からカンスト (無双・爽快感)</option>
              <option value="段階的覚醒">段階的覚醒 (王道少年漫画)</option>
              <option value="どん底下克上">どん底下克上 (追放・復讐・大逆転)</option>
              <option value="頭脳戦特化">頭脳戦特化 (能力は弱いが機転で勝利)</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">チート度 (1〜5): {cheatScale}</label>
            <input
              type="range"
              min={1}
              max={5}
              value={cheatScale}
              onChange={(e) => setCheatScale(Number(e.target.value))}
              className="w-full accent-sky-500"
              disabled={isLoading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">代償・世界リスク過酷度 (1〜5): {costSeverity}</label>
            <input
              type="range"
              min={1}
              max={5}
              value={costSeverity}
              onChange={(e) => setCostSeverity(Number(e.target.value))}
              className="w-full accent-amber-500"
              disabled={isLoading}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">システム支援度 (0〜100): {systemAssist}</label>
          <input
            type="range"
            min={0}
            max={100}
            value={systemAssist}
            onChange={(e) => setSystemAssist(Number(e.target.value))}
            className="w-full accent-emerald-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">目標話数 (1〜100): {targetChapters}</label>
          <input
            type="range"
            min={1}
            max={100}
            value={targetChapters}
            onChange={(e) => setTargetChapters(Number(e.target.value))}
            className="w-full accent-purple-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">あらすじ・コアアイデア</label>
          <textarea
            rows={4}
            className="w-full p-2.5 rounded bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-sky-500"
            placeholder="主人公の特技、最初の事件、物語のゴールなどを自由に記述"
            value={synopsis}
            onChange={(e) => setSynopsis(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-3 bg-sky-600 hover:bg-sky-500 disabled:bg-sky-900 disabled:cursor-not-allowed rounded font-semibold text-white transition-colors"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              AIアイデア生成中...
            </span>
          ) : (
            '次へ: 五感ビートとクリフハンガー構成を自動設計する →'
          )}
        </button>
      </form>
    </div>
  );
};