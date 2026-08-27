import React, { useState, useEffect } from 'react';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { NsfwDisclaimerModal } from '@/components/dialogs/NsfwDisclaimerModal';
import { getPlanningOptions } from '@/api';
import type { EasyModeParams, PlanningOptions } from '@/types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: EasyModeParams) => void;
}

const DEFAULT_EASY_GENRES: Record<string, { genre: string; archetype: string; desc: string }> = {
  "⚔️ 追放ざまぁ":    { genre: "ファンタジー", archetype: "王道ざまぁ（爽快感最大）", desc: "不当に追放された主人公が成り上がり、元の仲間を見返す爽快ストーリー" },
  "🌸 悪役令嬢":      { genre: "恋愛",         archetype: "悪役令嬢の逆転劇", desc: "乙女ゲームに転生した令嬢が破滅フラグを回避しながら逆転を狙う" },
  "🔄 死に戻り":      { genre: "ファンタジー", archetype: "死に戻り（絶望と執念）", desc: "何度も死に戻りながら完璧な結末を目指す絶望と執念のループ作品" },
  "🍲 ほのぼのスローライフ": { genre: "ファンタジー", archetype: "ほのぼの飯テロ（ストレス皆無）", desc: "異世界でのんびりと料理や農業を楽しむ癒し系スローライフ" },
  "⚡ 勘違い無双":    { genre: "ファンタジー", archetype: "勘違い爆走（ギャップ萌え）", desc: "本人の意図と周囲の評価がズレまくるコメディ展開" },
  "🐾 最強テイマー":  { genre: "ファンタジー", archetype: "最強テイマー（もふもふ無双）", desc: "愛らしい魔獣たちを引き連れてマイペースに冒険する作品" },
  "🌸 純愛官能":      { genre: "官能/ロマンス", archetype: "純愛官能（情緒重視）", desc: "情緒と余韻を重んじる純愛官能ストーリー" },
  "💜 背徳官能":      { genre: "官能/ロマンス", archetype: "背徳官能（心理葛藤重視）", desc: "タブーに挑む心理葛藤と背徳感を重ずした大人向け劇" },
  "✨ 幻想官能":      { genre: "官能/ロマンス", archetype: "ファンタジー官能（異種族・魔法感覚）", desc: "異種族の身体感覚と魔法を交えたファンタジー官能" },
  "💑 夫婦官能":      { genre: "官能/ロマンス", archetype: "夫婦/既婚官能（日常情緒）", desc: "夫婦の親密性の深化と日常の情緒" },
};

const DEFAULT_STORY_ARCHETYPES = [
  "王道ざまぁ（爽快感最大）",
  "悪役令嬢の逆転劇",
  "死に戻り（絶望と執念）",
  "ほのぼの飯テロ（ストレス皆無）",
  "勘違い爆走（ギャップ萌え）",
  "最強テイマー（もふもふ無双）",
  "万能錬金術師（商会成り上がり）",
  "現代知識チート（文明無双）",
  "ダンジョン配信（現代バズ）",
  "本格戦記（泥臭い逆転）",
  "純愛官能（情緒重視）",
  "背徳官能（心理葛藤重視）",
  "ファンタジー官能（異種族・魔法感覚）",
  "夫婦/既婚官能（日常情緒）",
];

const ARCHETYPE_LABEL_MAP: Record<string, string> = {
  overcoming_the_monster: "王道ざまぁ（爽快感最大）",
  rags_to_riches: "悪役令嬢の逆転劇",
  tragedy: "死に戻り（絶望と執念）",
  rebirth: "ほのぼの飯テロ（ストレス皆無）",
  the_quest: "冒険の旅（王道ファンタジー）",
  voyage_and_return: "異世界往還（現代・異世界行き来）",
  comedy: "コメディ・日常（爆笑・ほのぼの）",
  pure_love_erotic: "純愛官能（情緒重視）",
  taboo_erotic: "背徳官能（心理葛藤重視）",
  fantasy_erotic: "ファンタジー官能（異種族・魔法感覚）",
  married_erotic: "夫婦/既婚官能（日常情緒）",
  avenger: "復讐・ざまぁ型",
  reincarnation: "異世界転生・無双型",
  villainess: "悪役令嬢型",
  struggler: "泥臭い逆転型",
};

const DEFAULT_STYLE_DEFINITIONS: Record<string, { name: string; description: string }> = {
  style_web_standard: { name: "Web小説標準（テンポ・会話重視）", description: "三行改行と会話劇を中心としたテンポ感あるスタイル" },
  style_literary: { name: "文学風（重厚・情緒描写）", description: "豊かな景物描写と心情の機微を紡ぐ重厚な文体" },
  style_light: { name: "ライトノベル風（口語・ポップ）", description: "キャッチーでテンポの良い軽快な文章スタイル" },
  style_villainess_elegant: { name: "悪役令嬢風（優雅・高貴）", description: "華やかで気品ある言葉遣いと皮肉を秘めた文体" },
  style_overlord: { name: "オーバーロード風（勘違い・荘厳）", description: "第三者視点の絶賛と主人公の内心ギャップを描く" },
  style_bookworm_daily: { name: "日常・スローライフ風（ほんわか）", description: "食事や生活のディテールを丁寧に描く癒やし文体" },
  style_cursed_sword: { name: "シリアス・ダーク風（冷酷・殺伐）", description: "緊迫感あふれる戦闘とシリアスな世界観" },
  style_onmyoji_master: { name: "和風ファンタジー（和装・伝奇）", description: "陰陽道や和の言葉遣いを交えた雰囲気あるスタイル" },
};

export function EasyModeDialog({ isOpen, onClose, onSubmit }: Props) {
  const {
    easyGenre,
    setEasyGenre,
    easyKeywords,
    setEasyKeywords,
    easyArchetype,
    setEasyArchetype,
    easyStyleKey,
    setEasyStyleKey,
    easyTargetEps,
    setEasyTargetEps,
    easyWordCount,
    setEasyWordCount,
    easyConcept,
    setEasyConcept,
    enableErotic,
    setEnableErotic,
    eroticIntensity,
    enableIllustration,
    setEnableIllustration,
    illustrationType,
    setIllustrationType,
    illustrationModel,
    setIllustrationModel,
    generateCover,
    setGenerateCover,
    generateEpisodeIllustrations,
    setGenerateEpisodeIllustrations,
    episodeInterval,
    setEpisodeInterval,
  } = useEasyModeStore();

  const { apiKey, setApiKey, nsfwConsented, setNsfwConsented } = useUserSettingsStore();
  const [apiKeyLocal, setApiKeyLocal] = useState(apiKey);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showNsfwModal, setShowNsfwModal] = useState(false);

  useEffect(() => {
    setApiKeyLocal(apiKey);
  }, [apiKey]);

  const hasApiKey = apiKeyLocal.trim().length >= 10;
  const [easyGenres, setEasyGenres] = useState<PlanningOptions['easy_genres']>(DEFAULT_EASY_GENRES);
  const [storyArchetypes, setStoryArchetypes] = useState<string[]>(DEFAULT_STORY_ARCHETYPES);
  const [styleDefinitions, setStyleDefinitions] = useState<Record<string, { name: string; description: string }>>(DEFAULT_STYLE_DEFINITIONS);
  const [selectedGenreKey, setSelectedGenreKey] = useState(Object.keys(DEFAULT_EASY_GENRES)[0]);

  useEffect(() => {
    if (!isOpen) return;
    getPlanningOptions()
      .then(data => {
        if (data.easy_genres && Object.keys(data.easy_genres).length > 0) {
          setEasyGenres(data.easy_genres);
          const firstKey = Object.keys(data.easy_genres)[0];
          setSelectedGenreKey(firstKey);
          if (data.easy_genres[firstKey]) {
            setEasyGenre(data.easy_genres[firstKey].genre);
            const rawArch = data.easy_genres[firstKey].archetype;
            setEasyArchetype(ARCHETYPE_LABEL_MAP[rawArch] || rawArch);
          }
        }
        if (data.story_archetypes && data.story_archetypes.length > 0) {
          setStoryArchetypes(data.story_archetypes);
        }
        if (data.style_definitions && Object.keys(data.style_definitions).length > 0) {
          setStyleDefinitions(data.style_definitions);
        }
      })
      .catch(err => {
        console.error('Failed to load easy genres, using default presets:', err);
      });
  }, [isOpen, setEasyGenre, setEasyArchetype, setEasyGenres, setSelectedGenreKey, setStoryArchetypes, setStyleDefinitions]);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  const handleGenreCardClick = (key: string) => {
    setSelectedGenreKey(key);
    const genreData = easyGenres[key];
    if (genreData) {
      setEasyGenre(genreData.genre);
      setEasyArchetype(genreData.archetype); // assuming archetype is already label (or we need mapping)
      // For safety, we can still apply mapping if needed:
      const mapped = ARCHETYPE_LABEL_MAP[genreData.archetype] || genreData.archetype;
      setEasyArchetype(mapped);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasApiKey) {
      // Focus on API key input if exists
      const apiKeyInput = document.getElementById('easy-api-key') as HTMLInputElement | null;
      if (apiKeyInput) {
        apiKeyInput.focus();
      }
      return;
    }
    setApiKey(apiKeyLocal.trim());
    onSubmit({
      api_key: '',
      config: {},
      initial_limit: 1,
      genre: easyGenre,
      keywords: easyKeywords,
      archetype_key: easyArchetype,
      style_key: easyStyleKey,
      target_eps: easyTargetEps,
      word_count: easyWordCount,
      concept: easyConcept,
      tone_vibe: 0.65,
      enableIllustration,
      illustrationType,
      illustrationModel,
      generateCover,
      generateEpisodeIllustrations,
      episodeInterval,
    });
  };

  const genreOptions = Object.keys(easyGenres);
  const currentDesc = easyGenres[selectedGenreKey]?.desc || '';

  return (
    /* オーバーレイ（背景）へのクリックでダイアログを閉じる意図的な実装。
         handleOverlayClick 内で e.target === e.currentTarget のみ発火するため、
         ダイアログ本体への誤クリックは無視される。 */
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="modal-overlay animate-fade-in"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <form
        className="glass-panel animate-slide-up w-[560px] p-7 flex flex-col gap-4 max-h-[92vh] overflow-y-auto"
        onSubmit={handleSubmit}
        style={{ backgroundColor: 'var(--bg-sidebar)' }}
      >
        <div className="border-b border-border pb-3">
          <h3 id="modal-title" className="text-lg font-bold text-white">
            ⚡ かんたんモードで小説を作る
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            ジャンルを選んでボタンを押すだけ。あとは AI が企画・プロット・本文まで自動で書きます。
          </p>
        </div>

        {/* ステップ表示 */}
        <ol className="flex items-center gap-2 text-[0.7rem] font-bold">
          <li className="flex items-center gap-1 px-2 py-1 rounded-full bg-indigo-500/20 text-indigo-200">
            <span className="w-4 h-4 rounded-full bg-indigo-500 text-white text-center leading-4">1</span> ジャンル
          </li>
          <li className="flex items-center gap-1 px-2 py-1 rounded-full bg-indigo-500/20 text-indigo-200">
            <span className="w-4 h-4 rounded-full bg-indigo-500 text-white text-center leading-4">2</span> キーワード（任意）
          </li>
          <li className="flex items-center gap-1 px-2 py-1 rounded-full bg-indigo-500/20 text-indigo-200">
            <span className="w-4 h-4 rounded-full bg-indigo-500 text-white text-center leading-4">3</span> 生成！
          </li>
        </ol>

        {/* 🔑 APIキー（ここで直接入力できるので迷わない） */}
        <div className={`rounded-lg border p-3.5 ${hasApiKey ? 'border-emerald-700/50 bg-emerald-950/20' : 'border-amber-600/60 bg-amber-950/20'}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-sm font-bold ${hasApiKey ? 'text-emerald-200' : 'text-amber-200'}`}>
              {hasApiKey ? '✅ Gemini APIキー（設定済み）' : '⚠️ Gemini APIキーが必要です'}
            </span>
          </div>
          <input
            id="easy-api-key"
            type="password"
            value={apiKeyLocal}
            onChange={(e) => setApiKeyLocal(e.target.value)}
            placeholder="AIza...  （Google AI Studio で無料取得）"
            className="w-full text-xs px-2.5 py-1.5 rounded bg-slate-950 text-white font-medium border border-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            aria-label="Gemini APIキーを入力"
          />
          {!hasApiKey && (
            <p className="text-[0.7rem] text-amber-300/90 mt-1.5">
              取得は無料です → <span className="font-mono">aistudio.google.com/app/apikey</span>
            </p>
          )}
        </div>

        {/* 1. ジャンル */}
        <div>
          <label htmlFor="easy-genre" className="block text-sm font-medium text-slate-200 mb-1">
            ① プリセット・ジャンル
          </label>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {genreOptions.map((key) => {
              const genreData = easyGenres[key];
              const isSelected = selectedGenreKey === key;
              return (
                <button
                  key={key}
                  onClick={() => handleGenreCardClick(key)}
                  className={`w-full aspect-[16/9] flex flex-col items-center justify-center border rounded-lg p-4 ${
                    isSelected
                      ? 'border-[var(--accent)] bg-[var(--accent)]/20 text-[var(--accent)]'
                      : 'border-[var(--border)] hover:bg-[var(--bg-muted)]'
                  }`}
                >
                  <div className="text-2xl font-bold mb-2">{genreData?.genre ?? key}</div>
                  <div className="text-sm text-center">{genreData?.archetype ?? ''}</div>
                </button>
              );
            })}
          </div>
          {currentDesc && (
            <p className="text-xs text-indigo-300 mt-1 bg-indigo-950/40 p-2 rounded border border-indigo-900/50">
              💡 {currentDesc}
            </p>
          )}
        </div>

        {/* 2. キーワード（任意） */}
        <div>
          <label htmlFor="easy-keywords" className="block text-sm font-medium text-slate-200 mb-1">
            ② キーワード <span className="text-[0.7rem] font-normal text-muted-foreground">（空欄でもOK）</span>
          </label>
          <input
            id="easy-keywords"
            type="text"
            value={easyKeywords}
            onChange={(e) => setEasyKeywords(e.target.value)}
            placeholder="例: 追放, 復讐, チート"
            className="w-full"
          />
          <p className="text-[0.7rem] text-muted-foreground mt-1">
            物語の核となる要素をカンマで区切って入力します。未入力の場合はジャンルから自動で決めます。
          </p>
        </div>

        {/* 詳細設定（折りたたみ） */}
        <div className="rounded-lg border border-slate-700/60 bg-slate-900/40">
          <button
            type="button"
            onClick={() => setShowAdvanced(v => !v)}
            aria-expanded={showAdvanced}
            className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-semibold text-slate-200 hover:bg-slate-800/40 rounded-lg"
          >
            <span>🔧 もっとこだわる（詳細設定・上級者向け）</span>
            <span className={`transition-transform ${showAdvanced ? 'rotate-180' : ''}`}>▾</span>
          </button>

          {showAdvanced && (
            <div className="px-4 pb-4 pt-1 flex flex-col gap-4 border-t border-slate-700/60 animate-fade-in">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="tooltip-container mb-1">
                    <label htmlFor="easy-archetype" className="block text-sm font-medium text-slate-200">物語の型</label>
                    <span className="tooltip-icon">?</span>
                    <span className="tooltip-text">物語全体の展開パターン（プロットの骨組み）です。</span>
                  </div>
                  <select
                    id="easy-archetype"
                    value={easyArchetype}
                    onChange={(e) => setEasyArchetype(e.target.value)}
                    className="w-full text-sm"
                  >
                    {storyArchetypes.map((arch) => {
                      const label = ARCHETYPE_LABEL_MAP[arch] || arch;
                      return (
                        <option key={arch} value={arch}>{label}</option>
                      );
                    })}
                  </select>
                </div>
                <div>
                  <div className="tooltip-container mb-1">
                    <label htmlFor="easy-style-key" className="block text-sm font-medium text-slate-200">文体スタイル</label>
                    <span className="tooltip-icon">?</span>
                    <span className="tooltip-text">文の雰囲気やキャラクターの会話のテンポ、地の文の硬さを調整します。</span>
                  </div>
                  <select
                    id="easy-style-key"
                    value={easyStyleKey}
                    onChange={(e) => setEasyStyleKey(e.target.value)}
                    className="w-full text-sm"
                  >
                    {Object.entries(styleDefinitions).map(([key, item]) => (
                      <option key={key} value={key}>{item.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="tooltip-container mb-1">
                    <label htmlFor="easy-target-eps" className="block text-sm font-medium text-slate-200">全体目標話数</label>
                    <span className="tooltip-icon">?</span>
                    <span className="tooltip-text">生成するエピソードの合計数です。3話〜100話の間で指定できます。</span>
                  </div>
                  <input
                    id="easy-target-eps"
                    type="number"
                    value={easyTargetEps}
                    onChange={(e) => setEasyTargetEps(parseInt(e.target.value) || 10)}
                    min={3}
                    max={100}
                    className="w-full"
                  />
                </div>
                <div>
                  <div className="tooltip-container mb-1">
                    <label htmlFor="easy-word-count" className="block text-sm font-medium text-slate-200">一話あたりの文字数</label>
                    <span className="tooltip-icon">?</span>
                    <span className="tooltip-text">各話ごとの本文のボリューム目安です（1000〜10000字）。</span>
                  </div>
                  <input
                    id="easy-word-count"
                    type="number"
                    value={easyWordCount}
                    onChange={(e) => setEasyWordCount(parseInt(e.target.value) || 3000)}
                    step={500}
                    min={1000}
                    max={10000}
                    className="w-full"
                  />
                </div>
              </div>

              {/* 🔞 官能表現 (NSFW) オプトイン設定 */}
              <div className="bg-rose-950/20 border border-rose-900/40 rounded-lg p-3.5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="tooltip-container">
                    <label htmlFor="enable-erotic" className="flex items-center gap-2 cursor-pointer text-sm font-semibold text-rose-200">
                      <input
                        id="enable-erotic"
                        type="checkbox"
                        checked={enableErotic}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          if (checked && !nsfwConsented) {
                            setShowNsfwModal(true);
                          } else {
                            setEnableErotic(checked);
                          }
                        }}
                        className="w-4 h-4 accent-rose-500 rounded cursor-pointer"
                      />
                      🔞 官能表現（R18/NSFW要素）を含める
                    </label>
                    <span className="tooltip-icon">?</span>
                    <span className="tooltip-text">チェックすると官能描写や濃厚な恋愛シーンを追加します。</span>
                  </div>
                  <span className="text-[0.7rem] text-rose-300 font-mono">
                    {enableErotic ? 'ON' : 'OFF'}
                  </span>
                </div>

                {enableErotic && (
                  <div className="space-y-2 pt-1 border-t border-rose-900/30 animate-fade-in">
                    <div className="flex justify-between items-center text-xs text-rose-200">
                      <div className="tooltip-container">
                        <label htmlFor="erotic-intensity" className="font-medium">官能の過激度 (Intensity)</label>
                        <span className="tooltip-icon">?</span>
                        <span className="tooltip-text">過激度が低いほどフェティシズムや焦らし・心理的葛藤に焦点が当たり、高くなるほど肉体的な直接描写が増えます。</span>
                      </div>
                      <span className="font-bold font-mono text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/50">
                        {eroticIntensity}: {['ほのぼの', '微熱', '情熱(標準)', '背徳', '濃厚', '過激(極限)'][eroticIntensity] || ''}
                      </span>
                    </div>
                    <div className="flex justify-between text-[0.65rem] text-slate-400 font-mono px-0.5">
                      <span>0: ほのぼの</span>
                      <span>2: 標準</span>
                      <span>5: 極限</span>
                    </div>
                  </div>
                )}
              </div>

              {/* 🎨 挿絵生成 オプトイン設定 */}
              <div className="bg-indigo-950/20 border border-indigo-900/40 rounded-lg p-3.5 space-y-3 animate-fade-in">
                <div className="flex items-center justify-between">
                  <label htmlFor="enable-illustration" className="flex items-center gap-2 cursor-pointer text-sm font-semibold text-indigo-200">
                    <input
                      id="enable-illustration"
                      type="checkbox"
                      checked={enableIllustration}
                      onChange={(e) => setEnableIllustration(e.target.checked)}
                      className="w-4 h-4 accent-indigo-500 rounded cursor-pointer"
                    />
                    🎨 挿絵を自動生成する
                  </label>
                  <span className="text-[0.7rem] text-indigo-300 font-mono">
                    {enableIllustration ? 'ON' : 'OFF'}
                  </span>
                </div>

                {enableIllustration && (
                  <div className="space-y-3 pt-2 border-t border-indigo-900/30">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label htmlFor="illustration-type" className="block text-xs font-medium text-indigo-200 mb-1">生成範囲</label>
                        <select
                          id="illustration-type"
                          value={illustrationType}
                          onChange={(e) => setIllustrationType(e.target.value as 'cover' | 'episode' | 'both')}
                          className="w-full text-xs"
                        >
                          <option value="cover">表紙のみ</option>
                          <option value="episode">話数ごと</option>
                          <option value="both">両方</option>
                        </select>
                      </div>
                      <div>
                        <label htmlFor="illustration-model" className="block text-xs font-medium text-indigo-200 mb-1">モデル品質</label>
                        <select
                          id="illustration-model"
                          value={illustrationModel}
                          onChange={(e) => setIllustrationModel(e.target.value as 'fast' | 'quality')}
                          className="w-full text-xs"
                        >
                          <option value="fast">高速 (Fast)</option>
                          <option value="quality">高品質 (Quality)</option>
                        </select>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="flex items-center gap-2 cursor-pointer text-xs text-indigo-200">
                            <input
                              type="checkbox"
                              checked={generateCover}
                              onChange={(e) => setGenerateCover(e.target.checked)}
                              className="w-3 h-3 accent-indigo-500"
                            />
                            表紙を生成する
                          </label>
                        </div>
                        <div className="flex items-center justify-between">
                          <label className="flex items-center gap-2 cursor-pointer text-xs text-indigo-200">
                            <input
                              type="checkbox"
                              checked={generateEpisodeIllustrations}
                              onChange={(e) => setGenerateEpisodeIllustrations(e.target.checked)}
                              className="w-3 h-3 accent-indigo-500"
                            />
                            話数ごとに挿絵を生成する
                          </label>
                        </div>
                        {generateEpisodeIllustrations && (
                          <div className="flex items-center gap-3 pt-1">
                            <label htmlFor="episode-interval" className="text-xs text-indigo-300">生成間隔 (話数ごと):</label>
                            <input
                              id="episode-interval"
                              type="number"
                              value={episodeInterval}
                              onChange={(e) => setEpisodeInterval(parseInt(e.target.value) || 1)}
                              min={1}
                              max={20}
                              className="w-16 text-xs px-1"
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <div className="tooltip-container mb-1">
                  <label htmlFor="easy-concept" className="block text-sm font-medium text-slate-200">コンセプト詳細 (チート内容や世界観など)</label>
                  <span className="tooltip-icon">?</span>
                  <span className="tooltip-text">「実は最強の魔法ハッカー」「魔王の娘と契約する」などの設定を自由に記述できます。</span>
                </div>
                <textarea
                  id="easy-concept"
                  value={easyConcept}
                  onChange={(e) => setEasyConcept(e.target.value)}
                  placeholder="例: 主人公は最強のハッカーだが異世界で魔法回路をハックする..."
                  rows={3}
                  className="w-full"
                  aria-label="コンセプト詳細"
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-1">
          <button type="button" className="btn btn-secondary transition-colors duration-200 flex-1" onClick={onClose}>
            キャンセル
          </button>
          <button type="submit" className="btn btn-primary transition-colors duration-200 flex-[2]" disabled={!hasApiKey}>
            {hasApiKey ? '🚀 生成開始' : '⚠️ APIキーを入力してください'}
          </button>
        </div>
        <p className="text-[0.7rem] text-muted-foreground text-center">
          生成には数十秒〜数分かかることがあります。進捗は画面右下のモニターで確認でき、完成した小説は「作品一覧」に表示されます。
        </p>
      </form>
      <NsfwDisclaimerModal
        isOpen={showNsfwModal}
        onAccept={() => {
          setEnableErotic(true);
          setNsfwConsented(true);
          setShowNsfwModal(false);
        }}
        onCancel={() => {
          setEnableErotic(false);
          setShowNsfwModal(false);
        }}
      />
    </div>
  );
}