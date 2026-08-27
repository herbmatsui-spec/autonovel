import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useBookStore } from '@/store/useBookStore';
import { useBooks } from '@/hooks/useBooks';
import { useAppActions } from '@/hooks/useAppActions';
import { getPlanningOptions } from '@/api';
import type { PlanningOptions } from '@/types/api';
import { toast } from 'sonner';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { useNavigate } from 'react-router-dom';
import { SettingsModal } from '@/components/dialogs/SettingsModal';
import { NsfwDisclaimerModal } from '@/components/dialogs/NsfwDisclaimerModal';

const DEFAULT_STYLE_DEFINITIONS: Record<string, { name: string; description: string }> = {
  style_web_standard: { name: 'Web小説標準（テンポ・会話重視）', description: '三行改行と会話劇を中心としたテンポ感あるスタイル' },
  style_serious_fantasy: { name: 'ハイファンタジー（重厚・生活感）', description: '回想的かつ内省的なトーン。五感を通じた生活感を重視' },
  style_psychological_loop: { name: '死に戻り・心理サスペンス（切迫・執念）', description: '呼吸音や絶叫を交え切迫した心理を畳み掛ける文体' },
  style_villainess_elegant: { name: '悪役令嬢（優雅・気品・皮肉）', description: '華やかで気品ある言葉遣いと皮肉を秘めた文体' },
  style_overlord: { name: '勘違い・魔王（オバロ風・荘厳）', description: '第三者視点の絶賛と主人公の内心ギャップを描く' },
  style_bookworm_daily: { name: '日常・スローライフ風（ほんわか・食事）', description: '食事や生活のディテールを丁寧に描く癒やし文体' },
  style_military_rational: { name: '戦記・合理的（硬質・軍事）', description: '感情を排した報告書的な文体。硬質な語彙と徹底した合理主義' },
  style_comedy_speed: { name: '高速コメディ（軽快・テンポ）', description: 'ボケとツッコミの応酬、地の文はテンポ重視' },
  style_dark_hero: { name: 'ダークヒーロー（冷酷・無双）', description: '敵には容赦ない断定的な暴力性、味方には甘いデレ' },
  style_iron_wall: { name: '鉄壁・重厚（タンク無双）', description: '金属の重みと衝撃、不動性を強調する重厚文体' },
  style_evolution: { name: '野生・進化（弱肉強食・捕食）', description: '生理的な飢えと進化の生々しさを動物的文体で記述' },
};

const GENRE_ICONS: Record<string, string> = {
  '⚔️ 追放ざまぁ': '⚔️',
  '🌸 悪役令嬢': '👑',
  '🔄 死に戻り': '⏳',
  '🍲 ほのぼのスローライフ': '🍲',
  '⚡ 勘違い無双': '⚡',
  '🐾 最強テイマー': '🐾',
  '🌸 純愛官能': '💖',
  '💜 背徳官能': '🔮',
  '✨ 幻想官能': '✨',
  '💑 夫婦官能': '💍',
};

const GENRE_BADGES: Record<string, string> = {
  '⚔️ 追放ざまぁ': '人気No.1・爽快感',
  '🌸 悪役令嬢': '女性向け人気・逆転劇',
  '🔄 死に戻り': '本格サスペンス・執念',
  '🍲 ほのぼのスローライフ': '癒し・飯テロ',
  '⚡ 勘違い無双': 'コメディ・爆笑',
  '🐾 最強テイマー': 'もふもふ・育成',
};

export default function LandingWizard() {
  const {
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
    setEroticIntensity,
    enableIllustration,
    setEnableIllustration,
    illustrationType,
    setIllustrationType,
  } = useEasyModeStore();

  const { apiKey, setApiKey, modelType, nsfwConsented, setNsfwConsented } = useUserSettingsStore();
  const { books } = useBooks();
  const { setSelectedBook } = useBookStore();
  const { setPendingEasyMode } = useWorkspaceStore();
  const { handleCreateEasyMode } = useAppActions(() => {});
  const navigate = useNavigate();

  const [options, setOptions] = useState<PlanningOptions | null>(null);
  const [selectedGenreKey, setSelectedGenreKey] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState(apiKey);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showNsfwModal, setShowNsfwModal] = useState(false);

  useEffect(() => {
    setApiKeyInput(apiKey);
  }, [apiKey]);

  useEffect(() => {
    getPlanningOptions()
      .then((data) => {
        if (data.easy_genres && Object.keys(data.easy_genres).length > 0) {
          setOptions(data);
          if (!selectedGenreKey) {
            const firstKey = Object.keys(data.easy_genres)[0];
            setSelectedGenreKey(firstKey);
            if (data.easy_genres[firstKey]) {
              setEasyGenre(data.easy_genres[firstKey].genre);
              const rawArch = data.easy_genres[firstKey].archetype;
              setEasyArchetype(rawArch);
            }
          }
        }
      })
      .catch((err) => {
        console.error('Failed to load planning options:', err);
        toast.error('ジャンル情報の読み込みに失敗しました。');
      });
  }, [setEasyGenre, setEasyArchetype, selectedGenreKey]);


  const hasApiKey = Boolean(apiKey && apiKey.trim().length >= 10);
  const hasValidInputApiKey = Boolean(apiKeyInput && apiKeyInput.trim().length >= 10);

  const handleSaveInlineApiKey = () => {
    if (!apiKeyInput || apiKeyInput.trim().length < 10) {
      toast.error('有効なGemini APIキーを入力してください');
      return;
    }
    setApiKey(apiKeyInput.trim());
    toast.success('APIキーを設定しました！');
  };

  const handleGenreCardClick = (key: string) => {
    setSelectedGenreKey(key);
    const genreData = options?.easy_genres?.[key];
    if (genreData) {
      setEasyGenre(genreData.genre);
      setEasyArchetype(genreData.archetype);
    }
    const styleRecMap: Record<string, string> = {
      '⚔️ 追放ざまぁ': 'style_web_standard',
      '🌸 悪役令嬢': 'style_villainess_elegant',
      '🔄 死に戻り': 'style_psychological_loop',
      '🍲 ほのぼのスローライフ': 'style_bookworm_daily',
      '⚡ 勘違い無双': 'style_overlord',
      '🐾 最強テイマー': 'style_web_standard',
      '🌸 純愛官能': 'style_literary',
      '💜 背徳官能': 'style_psychological_loop',
    };
    if (styleRecMap[key]) {
      setEasyStyleKey(styleRecMap[key]);
    }
  };

  const handleQuickResume = (book: typeof books[0]) => {
    setSelectedBook(book);
    navigate(`/book/${book.id}`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // If API key is entered in inline input but not yet saved, save it now
    if (!hasApiKey && hasValidInputApiKey) {
      setApiKey(apiKeyInput.trim());
    } else if (!hasApiKey && !hasValidInputApiKey) {
      toast.error('STEP 1 でGemini APIキーを設定してください。');
      return;
    }

    if (!options) {
      toast.error('ジャンル情報を読み込み中です。少々お待ちください。');
      return;
    }

    setIsSubmitting(true);
    setPendingEasyMode(true);
    handleCreateEasyMode()
      .then(() => {
        toast.success('小説の自動生成を開始しました！');
      })
      .catch((err) => {
        console.error('Easy mode generation failed:', err);
        toast.error('生成の開始に失敗しました。');
        setPendingEasyMode(false);
      })
      .finally(() => {
        setIsSubmitting(false);
      });
  };

  const genreOptions = options ? Object.keys(options.easy_genres) : [];
  const stylesMap = options?.style_definitions && Object.keys(options.style_definitions).length > 0
    ? options.style_definitions
    : DEFAULT_STYLE_DEFINITIONS;

  return (
    <div className="w-full pb-16 animate-fade-in space-y-8">
      {/* Top Banner / Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#181c2e] via-[#121520] to-[#0c0e14] border border-slate-700/60 p-6 sm:p-10 shadow-2xl">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
            <span>✨ AI自律型長編小説生成システム</span>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
            <span>かんたん3ステップ</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            ボタン1つで、AIがプロットから本文まで<br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
              完全自動で執筆します
            </span>
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
            初めての方でも大丈夫。APIキーを設定してジャンルを選ぶだけで、AIがキャラクター設定・全話プロット・各話の本文を自律的に書き上げます。
          </p>
        </div>

        {/* Ambient background glow */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Recent Books Quick Access (If exists) */}
      {books && books.length > 0 && (
        <div className="bg-[#121520] border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <span>📚 最近作成した作品</span>
              <span className="text-xs font-normal text-slate-400">（クリックして執筆・確認を再開）</span>
            </h3>
            <button
              onClick={() => navigate('/books')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
            >
              すべて見る ({books.length}件) →
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {books.slice(0, 3).map((book) => (
              <button
                key={book.id}
                onClick={() => handleQuickResume(book)}
                className="p-3 rounded-xl border border-slate-800 bg-[#161926] hover:border-indigo-500/50 hover:bg-slate-800/80 transition-all text-left group flex items-center justify-between"
              >
                <div className="truncate pr-2">
                  <div className="text-xs font-bold text-white group-hover:text-indigo-300 truncate">
                    #{book.id} {book.title}
                  </div>
                  <div className="text-[0.7rem] text-slate-400 mt-0.5">
                    {book.genre} • {book.target_eps}話予定
                  </div>
                </div>
                <span className="text-xs text-slate-500 group-hover:text-indigo-400 transition-colors">▶</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 3-Step Wizard Form */}
      <form onSubmit={handleSubmit} className="space-y-8">
        {/* STEP 1: API Key */}
        <div className={`rounded-2xl border transition-all p-6 ${
          hasApiKey
            ? 'bg-[#121622] border-emerald-800/40 shadow-sm'
            : 'bg-[#1a1622] border-amber-500/50 shadow-lg shadow-amber-500/5'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-sm ${
                hasApiKey ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
              }`}>
                1
              </div>
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <span>AI接続設定 (Gemini APIキー)</span>
                  {hasApiKey ? (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700/50">
                      ✅ 設定済み
                    </span>
                  ) : (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-600/50 animate-pulse">
                      ⚠️ 要設定
                    </span>
                  )}
                </h2>
                <p className="text-xs text-slate-400">
                  AIモデル「{modelType === 'gemini' ? 'Google Gemini' : 'OpenAI'}」と通信するためのキーです。
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-400 hover:text-indigo-300 underline font-medium flex items-center gap-1"
              >
                無料キーの取得はこちら ↗
              </a>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsSettingsOpen(true)}
                className="text-xs bg-[#161922] border-slate-700 hover:bg-slate-800 text-slate-300 h-8"
              >
                ⚙️ 設定パネルを開く
              </Button>
            </div>
          </div>

          {!hasApiKey ? (
            <div className="mt-4 p-4 rounded-xl bg-amber-950/20 border border-amber-600/30 space-y-3">
              <div className="text-xs text-amber-200 leading-relaxed">
                Google AI Studioで作成したAPIキー（<code className="bg-black/40 px-1 py-0.5 rounded text-amber-100 font-mono">AIzaSy...</code> で始まる文字列）を貼り付けて「保存」を押してください。取得は完全無料・クレジットカード不要です。
              </div>
              <div className="flex gap-2">
                <Input
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  placeholder="AIzaSy... （ここに貼り付け）"
                  className="flex-1 text-xs bg-black/50 border-amber-500/40 text-white font-mono"
                />
                <Button
                  type="button"
                  onClick={handleSaveInlineApiKey}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4"
                >
                  保存する
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between bg-black/20 px-4 py-2.5 rounded-xl border border-slate-800 text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <span className="text-emerald-400">●</span>
                <span>登録キー: <code className="font-mono text-slate-300">{apiKey.slice(0, 6)}...{apiKey.slice(-4)}</code></span>
              </div>
              <button
                type="button"
                onClick={() => setIsSettingsOpen(true)}
                className="text-indigo-400 hover:text-indigo-300 underline"
              >
                キーを変更する
              </button>
            </div>
          )}
        </div>

        {/* STEP 2: Genre & Archetype Selection */}
        <div className="rounded-2xl border border-slate-800 bg-[#121520] p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold text-sm">
              2
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">ジャンル＆ストーリー型を選ぶ</h2>
              <p className="text-xs text-slate-400">
                書きたい小説のジャンルを1つクリックしてください。AIが最適な構成・読者ウケする展開を自動で設計します。
              </p>
            </div>
          </div>

          {/* Genre Card Grid */}
          <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {genreOptions.map((key) => {
              const genreData = options?.easy_genres?.[key];
              const isSelected = selectedGenreKey === key;
              const icon = GENRE_ICONS[key] || '📖';
              const badge = GENRE_BADGES[key];

              return (
                <button
                  type="button"
                  key={key}
                  onClick={() => handleGenreCardClick(key)}
                  className={`relative w-full p-4 rounded-2xl border text-left transition-all duration-200 flex flex-col justify-between ${
                    isSelected
                      ? 'border-indigo-500 bg-gradient-to-br from-indigo-950/60 to-purple-950/40 shadow-lg shadow-indigo-500/10 ring-2 ring-indigo-500/80 scale-[1.01]'
                      : 'border-slate-800 bg-[#161926] hover:border-slate-700 hover:bg-slate-800/60'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-2xl">{icon}</span>
                      {isSelected ? (
                        <span className="text-xs font-bold text-indigo-300 bg-indigo-500/30 px-2 py-0.5 rounded-full border border-indigo-400/40">
                          ✓ 選択中
                        </span>
                      ) : badge ? (
                        <span className="text-[0.65rem] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-full">
                          {badge}
                        </span>
                      ) : null}
                    </div>
                    <div className="font-bold text-white text-base">
                      {genreData?.genre ?? key}
                    </div>
                    <div className="text-xs text-indigo-300/90 font-medium mt-0.5">
                      {genreData?.archetype ?? ''}
                    </div>
                  </div>

                  {genreData?.desc && (
                    <div className="text-[0.75rem] text-slate-400 mt-3 pt-2.5 border-t border-slate-800/80 leading-snug">
                      {genreData.desc}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Keywords (Optional) */}
          <div className="pt-2 border-t border-slate-800/80 space-y-2">
            <label className="font-semibold text-white text-sm flex items-center justify-between">
              <span>🏷️ こだわりキーワード・要素（任意）</span>
              <span className="text-xs text-slate-400 font-normal">未入力でも自動生成されます</span>
            </label>
            <Input
              value={easyKeywords}
              onChange={(e) => setEasyKeywords(e.target.value)}
              placeholder="例: 追放, 鑑定チート, 幼馴染, 飯テロ, もふもふ"
              className="w-full bg-[#161926] border-slate-700 text-white placeholder:text-slate-500"
            />
            <p className="text-[0.75rem] text-slate-400">
              物語に必ず入れたい要素や設定があればカンマ区切りで入力してください。
            </p>
          </div>

          {/* Advanced Accordion */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors py-1"
            >
              <span>{showAdvanced ? '▼' : '▶'}</span>
              <span>詳細設定（話数・文字数・文体・挿絵等）を変更する</span>
            </button>

            {showAdvanced && (
              <div className="mt-3 p-5 rounded-2xl bg-[#161926] border border-slate-800 space-y-5 animate-slide-up">
                {/* 1. 文体スタイル選択 (Style Key) */}
                <div className="space-y-2 p-3.5 rounded-xl bg-[#121520] border border-indigo-950/60">
                  <div className="flex items-center justify-between">
                    <label htmlFor="easy-style-select" className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                      <span>🖋️ 文体・執筆スタイル (文体DNA)</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => navigate('/style-lab')}
                      className="text-[0.7rem] text-indigo-400 hover:text-indigo-300 font-medium underline flex items-center gap-1"
                    >
                      🧪 文体ラボで新規作成・管理 ↗
                    </button>
                  </div>
                  <select
                    id="easy-style-select"
                    value={easyStyleKey}
                    onChange={(e) => setEasyStyleKey(e.target.value)}
                    className="w-full text-xs bg-[#1a1d2e] border border-slate-700 text-white rounded-lg p-2.5 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    {Object.entries(stylesMap).map(([key, item]) => (
                      <option key={key} value={key}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                  {stylesMap[easyStyleKey]?.description && (
                    <div className="text-[0.7rem] text-slate-300 bg-indigo-950/30 p-2.5 rounded-lg border border-indigo-900/40 leading-relaxed">
                      💡 <span className="font-semibold text-indigo-200">文体の特徴:</span> {stylesMap[easyStyleKey].description}
                    </div>
                  )}
                </div>

                {/* 2. 物語の型 (Archetype) & コンセプト */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="easy-archetype-select" className="text-xs font-medium text-slate-300 block mb-1">
                      📖 物語の展開パターン（型）:
                    </label>
                    <select
                      id="easy-archetype-select"
                      value={easyArchetype}
                      onChange={(e) => setEasyArchetype(e.target.value)}
                      className="w-full text-xs bg-[#121520] border border-slate-700 text-white rounded-lg p-2.5 focus:border-indigo-500 focus:outline-none"
                    >
                      {(options?.story_archetypes || [
                        '王道ざまぁ（爽快感最大）',
                        '悪役令嬢の逆転劇',
                        '死に戻り（絶望と執念）',
                        'ほのぼの飯テロ（ストレス皆無）',
                        '勘違い爆走（ギャップ萌え）',
                        '最強テイマー（もふもふ無双）',
                        '万能錬金術師（商会成り上がり）',
                        '現代知識チート（文明無双）',
                        'ダンジョン配信（現代バズ）',
                        '本格戦記（泥臭い逆転）',
                      ]).map((arch) => (
                        <option key={arch} value={arch}>
                          {arch}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="easy-concept-input" className="text-xs font-medium text-slate-300 block mb-1">
                      💡 独自コンセプト・あらすじ構想（任意）:
                    </label>
                    <Input
                      id="easy-concept-input"
                      value={easyConcept}
                      onChange={(e) => setEasyConcept(e.target.value)}
                      placeholder="例: 世界樹が枯れた世界で林業チート"
                      className="text-xs bg-[#121520] border-slate-700 text-white"
                    />
                  </div>
                </div>

                {/* 3. 話数・文字数スライダー */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-800/80">
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-medium text-slate-300">
                        目標話数: <span className="text-indigo-300 font-bold">{easyTargetEps}話</span>
                      </label>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="20"
                      value={easyTargetEps}
                      onChange={(e) => setEasyTargetEps(parseInt(e.target.value) || 3)}
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[0.65rem] text-slate-500 font-mono">
                      <span>短編 (1話)</span>
                      <span>標準 (3〜5話)</span>
                      <span>長編 (20話)</span>
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs font-medium text-slate-300">
                        1話あたりの目標文字数: <span className="text-indigo-300 font-bold">{easyWordCount}文字</span>
                      </label>
                    </div>
                    <input
                      type="range"
                      min="1000"
                      max="6000"
                      step="500"
                      value={easyWordCount}
                      onChange={(e) => setEasyWordCount(parseInt(e.target.value) || 2500)}
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[0.65rem] text-slate-500 font-mono">
                      <span>1,000字 (サクッと)</span>
                      <span>2,500字 (Web標準)</span>
                      <span>6,000字 (重厚)</span>
                    </div>
                  </div>
                </div>

                {/* 4. 挿絵 & 官能表現 (NSFW) オプトイン */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-800/80">
                  {/* 挿絵設定 */}
                  <div className="p-3 rounded-xl bg-[#121520] border border-slate-800 space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-200">
                      <input
                        type="checkbox"
                        checked={enableIllustration}
                        onChange={(e) => setEnableIllustration(e.target.checked)}
                        className="w-3.5 h-3.5 accent-indigo-500 rounded cursor-pointer"
                      />
                      <span>🎨 AI挿絵・表紙を自動生成する</span>
                    </label>
                    {enableIllustration && (
                      <div className="space-y-2 pt-1 border-t border-slate-800 animate-fade-in text-[0.75rem]">
                        <div className="flex items-center justify-between text-slate-300">
                          <span>生成タイプ:</span>
                          <select
                            value={illustrationType}
                            onChange={(e) => setIllustrationType(e.target.value as 'cover' | 'episode' | 'both')}
                            className="bg-[#1a1d2e] border border-slate-700 rounded px-2 py-0.5 text-xs text-white"
                          >
                            <option value="cover">表紙のみ</option>
                            <option value="episode">各話挿絵のみ</option>
                            <option value="both">表紙 + 挿絵</option>
                          </select>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 官能表現設定 */}
                  <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-900/40 space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-rose-200">
                        <input
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
                          className="w-3.5 h-3.5 accent-rose-500 rounded cursor-pointer"
                        />
                        <span>🔞 官能・情愛描写 (NSFW) を含める</span>
                      </label>
                      <span className="text-[0.65rem] text-rose-300 font-mono">
                        {enableErotic ? 'ON' : 'OFF'}
                      </span>
                    </div>
                    {enableErotic && (
                      <div className="space-y-1.5 pt-1 border-t border-rose-900/30 animate-fade-in text-[0.75rem]">
                        <div className="flex justify-between items-center text-rose-300">
                          <span>過激度:</span>
                          <span className="font-bold font-mono text-rose-300 bg-rose-950 px-1.5 py-0.5 rounded border border-rose-800/40 text-[0.65rem]">
                            {['ほのぼの', '微熱', '情熱(標準)', '背徳', '濃厚', '過激(極限)'][eroticIntensity] || ''}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="5"
                          value={eroticIntensity}
                          onChange={(e) => setEroticIntensity(parseInt(e.target.value) || 2)}
                          className="w-full accent-rose-500 cursor-pointer"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* STEP 3: Generate Execution */}
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-[#121520] to-[#161a29] p-6 sm:p-8 shadow-xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold text-sm">
              3
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">自動執筆をスタートする</h2>
              <p className="text-xs text-slate-400">
                準備が完了しました。下のボタンを押すとAIが執筆を開始します。
              </p>
            </div>
          </div>

          <div className="pt-2">
            <Button
              type="submit"
              size="lg"
              disabled={isSubmitting || !hasApiKey || !options}
              className={`w-full py-6 text-base sm:text-lg font-bold rounded-xl shadow-xl transition-all ${
                isSubmitting
                  ? 'bg-indigo-700 text-white cursor-wait'
                  : hasApiKey && options
                  ? 'bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-500 hover:via-purple-500 hover:to-pink-500 text-white shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-[1.01]'
                  : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
              }`}
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center gap-3">
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>AI執筆タスクを作成中...</span>
                </div>
              ) : hasApiKey && options ? (
                <span>🚀 「{selectedGenreKey ?? '選択ジャンル'}」の小説を自動生成する</span>
              ) : (
                <span>⚠️ STEP 1でAPIキーを設定すると生成を開始できます</span>
              )}
            </Button>

            <div className="flex items-center justify-center gap-4 text-xs text-slate-400 mt-3 text-center">
              <span>⏱️ 生成所要時間: 数十秒〜数分</span>
              <span>•</span>
              <span>進捗は画面下部の進捗バーで常時確認可能</span>
            </div>
          </div>
        </div>
      </form>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <SettingsModal
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}

      {/* NSFW Consent Modal */}
      <NsfwDisclaimerModal
        isOpen={showNsfwModal}
        onAccept={() => {
          setNsfwConsented(true);
          setEnableErotic(true);
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