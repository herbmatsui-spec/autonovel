import { useState, useEffect } from 'react';
import {
  analyzeStyleDna,
  getCustomStyles,
  saveCustomStyle,
  deleteCustomStyle,
  getStyleFragments,
  addStyleFragment,
  deleteStyleFragment,
  getStylePresets,
} from '@/api';
import type { CustomStyle, StyleFragment, StylePresetsResponse } from '@/types/api';
import { toast } from 'sonner';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useNavigate } from 'react-router-dom';

interface AnalysisData {
  name?: string;
  instruction?: string;
  score?: number;
  analysis?: string;
  suggested_style_key?: string;
  metrics?: {
    dialogue_ratio?: string;
    avg_chars_per_line?: number;
    total_chars?: number;
  };
}

const SAMPLE_PRESETS = [
  {
    title: '追放ざまぁ・テンポ重視',
    tag: 'Payoff',
    text: `「クルト、貴様は本日をもって当パーティーから追放だ」\n\n勇者エリオットの冷たい声が、薄暗いギルドの個室に響いた。\n周囲の仲間たちも、嘲笑を浮かべながら俺を見下ろしている。\n\n「……理由を聞かせてもらってもいいか？」\n「理由だと？ ハッ、足手まといだからに決まっているだろう！ お前の【荷物持ち】スキルなど、魔王軍との決戦には何の役にも立たん！」\n\nエリオットは吐き捨てるように笑った。\n俺は静かに頷き、荷物を背負い直す。\n\n「分かった。今まで世話になったな」\n\n（――まさか、俺の【無限収納】がパーティー全員のステータスを10倍に底上げしていたことに、まだ気づいていないのか？）\n\nギルドの重い扉を押し開けた瞬間、俺の目の前に青いウィンドウが展開した。\n【真のスキル『神域創造』が解放されました】\n\n――ここから、俺の本当の物語が始まる。`,
  },
  {
    title: '悪役令嬢・気品と皮肉',
    tag: 'Love',
    text: `「エレオノーラ！ 貴様のような性悪な女との婚約など、今この場で破棄させてもらう！」\n\nきらびやかな夜会の中心で、第二王子エドワード様が高らかに宣言なさいました。\nその傍らには、怯えた小鹿のように王子の腕にしがみつく男爵令嬢の姿。\n\n周囲の貴族たちがざわめき、好奇と侮蔑の視線がわたくしへと集中いたします。\nわたくしは、扇でそっと口元を隠しながら、優雅に淑女の礼（カーテシー）を執りました。\n\n「殿下。公衆の面前でのお戯れは、王家の品位を損ねますことよ？」\n「黙れ！ 貴様がマリアを階段から突き落としたことは分かっているのだ！」\n「まあ。あのような平坦な絨毯の上で転ばれたことを、わたくしのせいにされますの？ 重力にすら嫌われていらっしゃるようですわね」\n\nわたくしが微笑みを深めると、王子は顔を真っ赤にして絶句いたしました。\nわたくしを誰だとお思いですの？ 帝国随一の魔導財閥を束ねるローゼンバーグ公爵家の長女ですわ。`,
  },
  {
    title: '重厚ファンタジー・五感描写',
    tag: 'Prep',
    text: `冷たい雨が、錆びついた鉄兜の縁を伝って首筋へと滴り落ちる。\n立ち込める泥の臭気と、わずかに焦げた松脂の煙。戦場跡に残された静寂は、死者たちの無言の抗議のように重く皮膚に張り付いていた。\n\nガルドは膝をつき、泥濘に埋もれた折れた長剣の柄を握りしめた。\n指先の感覚はすでに失われている。\n魔力を限界まで絞り尽くした後の虚脱感が、胃の腑に鈍い鉛の塊となって沈んでいた。\n\n「……生き残ったか」\n\n誰に向けるでもなく呟いた声は、霧雨の湿った空気に吸い込まれて消えた。\n遠く、天空へと聳え立つ光層都市のシルエットが、雷光に照らされて一瞬だけ白銀に輝く。\n世界は滅びに向かっている。だが、立ち止まることは許されない。`,
  },
];

type LabTab = 'analyze' | 'custom' | 'rag' | 'catalog';

export default function StyleLabTab() {
  const { apiKey } = useUserSettingsStore();
  const { setEasyStyleKey } = useEasyModeStore();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<LabTab>('analyze');

  // Analyze Tab State
  const [sample, setSample] = useState('');
  const [result, setResult] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [isSavingCustom, setIsSavingCustom] = useState(false);

  // Custom Styles State
  const [customStyles, setCustomStyles] = useState<CustomStyle[]>([]);
  const [loadingCustom, setLoadingCustom] = useState(false);

  // RAG Fragments State
  const [fragments, setFragments] = useState<StyleFragment[]>([]);
  const [loadingFragments, setLoadingFragments] = useState(false);
  const [ragTag, setRagTag] = useState('Payoff');
  const [ragContent, setRagContent] = useState('');
  const [isAddingFragment, setIsAddingFragment] = useState(false);

  // Catalog State
  const [presets, setPresets] = useState<StylePresetsResponse | null>(null);
  const [selectedPresetKey, setSelectedPresetKey] = useState<string>('style_web_standard');

  // Load Custom Styles
  const loadCustomList = async () => {
    try {
      setLoadingCustom(true);
      const data = await getCustomStyles();
      setCustomStyles(data);
    } catch (err) {
      console.error('Failed to load custom styles:', err);
    } finally {
      setLoadingCustom(false);
    }
  };

  // Load RAG Fragments
  const loadFragmentList = async () => {
    try {
      setLoadingFragments(true);
      const data = await getStyleFragments();
      setFragments(data);
    } catch (err) {
      console.error('Failed to load style fragments:', err);
    } finally {
      setLoadingFragments(false);
    }
  };

  // Load Catalog
  const loadCatalog = async () => {
    if (!presets) {
      try {
        const data = await getStylePresets();
        setPresets(data);
        if (data.styles && Object.keys(data.styles).length > 0) {
          setSelectedPresetKey(Object.keys(data.styles)[0]);
        }
      } catch (err) {
        console.error('Failed to load style presets:', err);
      }
    }
  };

  useEffect(() => {
    if (activeTab === 'custom') {
      loadCustomList();
    } else if (activeTab === 'rag') {
      loadFragmentList();
    } else if (activeTab === 'catalog') {
      loadCatalog();
    }
  }, [activeTab]);

  const handleAnalyze = async () => {
    if (!sample.trim()) {
      toast.warning('分析したい小説テキストを入力してください。');
      return;
    }
    if (!apiKey || apiKey.length < 10) {
      toast.warning('有効なAPIキーを設定してください（右上の「設定」から入力できます）。');
      return;
    }
    try {
      setLoading(true);
      const data = await analyzeStyleDna(sample);
      setResult(data as unknown as AnalysisData);
      setSaveName(data.name || 'マイカスタム文体');
      toast.success('文体DNAの分析が完了しました！');
    } catch (err: unknown) {
      toast.error('分析に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToCustom = async () => {
    if (!result) return;
    if (!saveName.trim()) {
      toast.error('文体名を入力してください。');
      return;
    }
    try {
      setIsSavingCustom(true);
      await saveCustomStyle({
        name: saveName.trim(),
        instruction: result.instruction || '',
        score: result.score || 80,
        analysis: result.analysis || '',
      });
      toast.success(`カスタム文体「${saveName}」を保存しました！初期画面の詳細設定から選択できます。`);
      setSaveName('');
    } catch (err: unknown) {
      toast.error('保存に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsSavingCustom(false);
    }
  };

  const handleDeleteCustom = async (id: number, name: string) => {
    if (!window.confirm(`カスタム文体「${name}」を削除してもよろしいですか？`)) return;
    try {
      await deleteCustomStyle(id);
      toast.success(`カスタム文体「${name}」を削除しました。`);
      loadCustomList();
    } catch (err: unknown) {
      toast.error('削除に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleAddFragment = async () => {
    if (!ragContent.trim()) {
      toast.warning('サンプル文章を入力してください。');
      return;
    }
    try {
      setIsAddingFragment(true);
      await addStyleFragment(
        {
          tag: ragTag,
          content: ragContent.trim(),
          origin: 'UserAdded',
        },
        apiKey
      );
      toast.success('文体サンプル断片をRAGに登録しました！');
      setRagContent('');
      loadFragmentList();
    } catch (err: unknown) {
      toast.error('登録に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsAddingFragment(false);
    }
  };

  const handleDeleteFragment = async (id: number) => {
    try {
      await deleteStyleFragment(id);
      toast.success('文体サンプル断片を削除しました。');
      loadFragmentList();
    } catch (err: unknown) {
      toast.error('削除に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  const handleApplyCustomStyle = (style: CustomStyle) => {
    setEasyStyleKey(`custom_${style.id}`);
    toast.success(`マイ文体「${style.name}」を適用しました！`);
    navigate('/landing');
  };

  return (
    <div className="w-full max-w-5xl mx-auto pb-16 animate-fade-in space-y-8">
      {/* Header Banner */}
      <div className="rounded-3xl bg-gradient-to-br from-[#191d30] via-[#131622] to-[#0c0e14] border border-slate-700/60 p-6 sm:p-8 shadow-2xl space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
          <span>🧪 文体DNAラボ & RAG管理システム</span>
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
          <span>Style Lab v3.6</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
          文体・文章の特徴をAIが精密解析 & 自律執筆に完全統合
        </h1>
        <p className="text-xs sm:text-sm text-slate-300 max-w-3xl leading-relaxed">
          お手持ちの小説から文体DNA（台詞比率・リズム・執筆指針）を抽出し、「マイ文体」として保存できます。
          さらに、シーン別文体RAGデータベースに登録してAIに黄金の質感を模倣させることが可能です。
        </p>

        {/* Sub Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab('analyze')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'analyze'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30 ring-1 ring-indigo-400'
                : 'bg-[#161926] text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>🧬 文体DNA抽出・分析</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('custom')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'custom'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30 ring-1 ring-indigo-400'
                : 'bg-[#161926] text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>⭐ 保存済みマイ文体</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('rag')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'rag'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30 ring-1 ring-indigo-400'
                : 'bg-[#161926] text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>📚 覇権文体RAGサンプル</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('catalog')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'catalog'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30 ring-1 ring-indigo-400'
                : 'bg-[#161926] text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>📖 プリセット文体カタログ</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: 文体DNA抽出・分析 */}
      {/* ========================================================================= */}
      {activeTab === 'analyze' && (
        <div className="space-y-6">
          {/* Input Panel */}
          <div className="rounded-2xl border border-slate-800 bg-[#121520] p-6 shadow-xl space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="style-sample-text" className="text-sm font-bold text-white flex items-center gap-2">
                  <span>📝 分析したい文章サンプルを入力</span>
                  <span className="text-xs text-slate-400 font-normal">（数百字〜数千字程度）</span>
                </label>
                <span className="text-xs text-slate-500 font-mono">
                  {sample.length} 文字
                </span>
              </div>

              {/* Quick Preset Buttons */}
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <span className="text-xs text-slate-400">サンプル例文:</span>
                {SAMPLE_PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSample(p.text)}
                    className="text-xs px-2.5 py-1 rounded-lg bg-[#1a1d2e] border border-slate-700 text-indigo-300 hover:border-indigo-500 hover:text-white transition-all"
                  >
                    {p.title}
                  </button>
                ))}
              </div>

              <textarea
                id="style-sample-text"
                value={sample}
                onChange={(e) => setSample(e.target.value)}
                rows={10}
                className="w-full text-xs sm:text-sm px-4 py-3 rounded-xl bg-[#161926] text-white border border-slate-700 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans leading-relaxed resize-y"
                placeholder="ここに分析したい文章を貼り付けてください..."
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setSample(''); setResult(null); }}
                className="text-xs border-slate-700 text-slate-400 hover:text-white"
              >
                クリア
              </Button>

              <Button
                variant="default"
                size="lg"
                onClick={handleAnalyze}
                disabled={loading || !sample.trim()}
                className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs sm:text-sm px-6 shadow-lg shadow-indigo-500/20"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>文体DNAを解析中...</span>
                  </div>
                ) : (
                  <span>🧬 文体DNAを分析する</span>
                )}
              </Button>
            </div>
          </div>

          {/* Analysis Result Display */}
          {result && (
            <div className="rounded-2xl border border-indigo-500/40 bg-gradient-to-b from-[#16192a] to-[#121520] p-6 sm:p-8 shadow-2xl space-y-6 animate-slide-up">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <div className="text-xs text-indigo-400 font-semibold uppercase tracking-wider mb-1">
                    Analysis Result
                  </div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-3">
                    <span>{result.name || '抽出文体'}</span>
                    {result.score !== undefined && (
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono font-bold">
                        スコア: {result.score}点
                      </span>
                    )}
                  </h2>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="default"
                    onClick={() => {
                      if (result.suggested_style_key) {
                        setEasyStyleKey(result.suggested_style_key);
                      }
                      navigate('/landing');
                    }}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4"
                  >
                    🚀 この文体で執筆を開始
                  </Button>
                </div>
              </div>

              {/* Save to Custom Style Bar */}
              <div className="p-4 rounded-xl bg-[#1a1d2e] border border-indigo-500/30 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                <div className="flex-1 space-y-1">
                  <div className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>⭐ この文体を「マイ文体」として保存する</span>
                  </div>
                  <div className="text-[0.7rem] text-slate-400">
                    保存すると、初期画面や企画立案の文体選択肢にいつでも表示されます。
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    value={saveName}
                    onChange={(e) => setSaveName(e.target.value)}
                    placeholder="文体名（例: 私のダークファンタジー体）"
                    className="text-xs bg-[#121520] border-slate-700 text-white w-56"
                  />
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleSaveToCustom}
                    disabled={isSavingCustom || !saveName.trim()}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3 font-semibold whitespace-nowrap"
                  >
                    {isSavingCustom ? '保存中...' : '保存'}
                  </Button>
                </div>
              </div>

              {/* Quantitative Metrics */}
              {result.metrics && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-4 rounded-xl bg-[#1a1d2e] border border-slate-800">
                    <div className="text-xs text-slate-400 mb-1">台詞比率</div>
                    <div className="text-lg font-bold text-indigo-300 font-mono">
                      {result.metrics.dialogue_ratio || '30%'}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-[#1a1d2e] border border-slate-800">
                    <div className="text-xs text-slate-400 mb-1">平均行文字数</div>
                    <div className="text-lg font-bold text-purple-300 font-mono">
                      {result.metrics.avg_chars_per_line || 35} 文字
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-[#1a1d2e] border border-slate-800 col-span-2 sm:col-span-1">
                    <div className="text-xs text-slate-400 mb-1">総分析文字数</div>
                    <div className="text-lg font-bold text-pink-300 font-mono">
                      {result.metrics.total_chars || sample.length} 文字
                    </div>
                  </div>
                </div>
              )}

              {/* Instruction */}
              {result.instruction && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">
                    ✍️ 文体模倣・執筆指針 (Prompt Instruction)
                  </h3>
                  <div className="p-4 rounded-xl bg-[#121520] border border-slate-800 text-xs sm:text-sm text-slate-200 leading-relaxed font-mono">
                    {result.instruction}
                  </div>
                </div>
              )}

              {/* Analysis Details */}
              {result.analysis && (
                <div className="space-y-2">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    📊 詳細分析レポート
                  </h3>
                  <div className="p-4 rounded-xl bg-[#121520] border border-slate-800 text-xs text-slate-300 leading-relaxed">
                    {result.analysis}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: 保存済みマイ文体管理 */}
      {/* ========================================================================= */}
      {activeTab === 'custom' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <span>⭐ 保存済みマイ文体一覧</span>
              <span className="text-xs font-normal text-slate-400 font-mono">
                ({customStyles.length}件)
              </span>
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={loadCustomList}
              className="text-xs border-slate-700 text-slate-300"
            >
              🔄 再読込
            </Button>
          </div>

          {loadingCustom ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              マイ文体を読み込み中...
            </div>
          ) : customStyles.length === 0 ? (
            <div className="rounded-2xl border border-slate-800 bg-[#121520] p-12 text-center space-y-3">
              <div className="text-3xl">📝</div>
              <h3 className="text-sm font-bold text-white">まだ保存されたマイ文体はありません</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                「文体DNA抽出・分析」タブでお手持ちの文章を分析し、「マイ文体として保存」を押すとここに登録されます。
              </p>
              <Button
                variant="default"
                size="sm"
                onClick={() => setActiveTab('analyze')}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs mt-2"
              >
                文体を分析しに行く →
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {customStyles.map((cs) => (
                <div
                  key={cs.id}
                  className="rounded-2xl border border-slate-800 bg-[#161926] p-5 space-y-3 hover:border-indigo-500/50 transition-all flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-white text-base truncate pr-2">
                        {cs.name}
                      </h3>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/40">
                        {cs.score}点
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-[#121520] border border-slate-800 text-xs text-slate-300 line-clamp-3 font-mono leading-relaxed">
                      {cs.instruction}
                    </div>

                    {cs.analysis && (
                      <div className="text-[0.7rem] text-slate-400 line-clamp-2">
                        💡 {cs.analysis}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
                    <button
                      type="button"
                      onClick={() => handleDeleteCustom(cs.id, cs.name)}
                      className="text-xs text-rose-400 hover:text-rose-300"
                    >
                      🗑️ 削除
                    </button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => handleApplyCustomStyle(cs)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
                    >
                      🚀 この文体で執筆
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: 覇権文体RAGサンプル管理 */}
      {/* ========================================================================= */}
      {activeTab === 'rag' && (
        <div className="space-y-6">
          {/* Register New Fragment */}
          <div className="rounded-2xl border border-slate-800 bg-[#121520] p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>➕ 理想の文章断片を文体RAGに登録</span>
              <span className="text-xs text-slate-400 font-normal">
                （執筆時にシーンに合わせてAIが自動で類似度検索して模倣します）
              </span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">シーン・感情タグ</label>
                <select
                  value={ragTag}
                  onChange={(e) => setRagTag(e.target.value)}
                  className="w-full text-xs bg-[#161926] border border-slate-700 text-white rounded-lg p-2"
                >
                  <option value="Payoff">ざまぁ・爽快カタルシス (Payoff)</option>
                  <option value="Hate">屈辱・ヘイト・追放 (Hate)</option>
                  <option value="Prep">修行・準備・日常 (Prep)</option>
                  <option value="Battle">緊迫・戦闘アクション (Battle)</option>
                  <option value="Comedy">コメディ・勘違い (Comedy)</option>
                  <option value="Love">純愛・心理葛藤 (Love)</option>
                </select>
              </div>

              <div className="sm:col-span-3">
                <label className="text-xs text-slate-400 block mb-1">文章サンプル（100〜500文字程度）</label>
                <textarea
                  value={ragContent}
                  onChange={(e) => setRagContent(e.target.value)}
                  rows={3}
                  className="w-full text-xs bg-[#161926] border border-slate-700 text-white rounded-lg p-2.5 focus:border-indigo-500 focus:outline-none"
                  placeholder="模倣させたい最高のリズムの文章を入力..."
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                variant="default"
                size="sm"
                onClick={handleAddFragment}
                disabled={isAddingFragment || !ragContent.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4"
              >
                {isAddingFragment ? '登録中...' : '📥 文体RAGに登録する'}
              </Button>
            </div>
          </div>

          {/* Fragments List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>🧬 登録済み文体RAG断片</span>
                <span className="text-xs font-mono text-slate-400">({fragments.length}件)</span>
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={loadFragmentList}
                className="text-xs border-slate-700 text-slate-300"
              >
                🔄 再読込
              </Button>
            </div>

            {loadingFragments ? (
              <div className="text-center py-8 text-slate-400 text-xs">読み込み中...</div>
            ) : fragments.length === 0 ? (
              <div className="rounded-xl border border-slate-800 bg-[#121520] p-8 text-center text-xs text-slate-400">
                まだ登録された文体サンプルはありません。上のフォームから追加してください。
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {fragments.map((frag) => (
                  <div
                    key={frag.id}
                    className="p-4 rounded-xl border border-slate-800 bg-[#161926] space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/50 font-bold text-[0.65rem]">
                        #{frag.tag}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteFragment(frag.id)}
                        className="text-[0.7rem] text-rose-400 hover:text-rose-300"
                      >
                        🗑️ 削除
                      </button>
                    </div>
                    <div className="text-slate-200 leading-relaxed line-clamp-4 font-mono bg-[#121520] p-2.5 rounded-lg border border-slate-800/80">
                      {frag.content}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: プリセット文体カタログ */}
      {/* ========================================================================= */}
      {activeTab === 'catalog' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Style Presets List */}
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-white mb-2">📚 組み込み文体一覧</h3>
              <div className="space-y-1.5 max-h-[600px] overflow-y-auto pr-1">
                {presets?.styles &&
                  Object.entries(presets.styles).map(([key, item]) => {
                    const isSelected = selectedPresetKey === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setSelectedPresetKey(key)}
                        className={`w-full text-left p-3 rounded-xl border transition-all text-xs flex items-center justify-between ${
                          isSelected
                            ? 'bg-indigo-950/60 border-indigo-500 text-white font-bold shadow-md'
                            : 'bg-[#161926] border-slate-800 text-slate-300 hover:border-slate-700'
                        }`}
                      >
                        <span className="truncate">{item.name}</span>
                        {item.dialogue_ratio && (
                          <span className="text-[0.65rem] font-mono text-slate-400">
                            台詞 {item.dialogue_ratio}
                          </span>
                        )}
                      </button>
                    );
                  })}
              </div>
            </div>

            {/* Right: Preset Details */}
            <div className="lg:col-span-2 space-y-4">
              {presets?.styles?.[selectedPresetKey] ? (
                <div className="rounded-2xl border border-slate-800 bg-[#121520] p-6 space-y-5 shadow-xl">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div>
                      <h2 className="text-lg font-bold text-white">
                        {presets.styles[selectedPresetKey].name}
                      </h2>
                      <span className="text-xs font-mono text-indigo-400">
                        key: {selectedPresetKey}
                      </span>
                    </div>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => {
                        setEasyStyleKey(selectedPresetKey);
                        toast.success(`文体「${presets.styles[selectedPresetKey].name}」を選択しました！`);
                        navigate('/landing');
                      }}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
                    >
                      🚀 この文体で執筆する
                    </Button>
                  </div>

                  {/* Instruction */}
                  <div className="space-y-1.5">
                    <div className="text-xs font-bold text-indigo-300">✍️ 執筆指針 (Instruction)</div>
                    <div className="p-3.5 rounded-xl bg-[#161926] border border-slate-800 text-xs text-slate-200 leading-relaxed font-mono">
                      {presets.styles[selectedPresetKey].instruction}
                    </div>
                  </div>

                  {/* Specific DNA Details */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {presets.styles[selectedPresetKey].syntax_rhythm && (
                      <div className="p-3 rounded-xl bg-[#161926] border border-slate-800 space-y-1">
                        <div className="font-semibold text-slate-400">構文・リズム</div>
                        <div className="text-slate-200">{presets.styles[selectedPresetKey].syntax_rhythm}</div>
                      </div>
                    )}
                    {presets.styles[selectedPresetKey].metaphor_dna && (
                      <div className="p-3 rounded-xl bg-[#161926] border border-slate-800 space-y-1">
                        <div className="font-semibold text-slate-400">比喩DNA</div>
                        <div className="text-slate-200">{presets.styles[selectedPresetKey].metaphor_dna}</div>
                      </div>
                    )}
                    {presets.styles[selectedPresetKey].noise_dna && (
                      <div className="p-3 rounded-xl bg-[#161926] border border-slate-800 space-y-1">
                        <div className="font-semibold text-slate-400">思考ノイズ・生理反応</div>
                        <div className="text-slate-200">{presets.styles[selectedPresetKey].noise_dna}</div>
                      </div>
                    )}
                    {presets.styles[selectedPresetKey].dialogue_ratio && (
                      <div className="p-3 rounded-xl bg-[#161926] border border-slate-800 space-y-1">
                        <div className="font-semibold text-slate-400">推奨台詞比率</div>
                        <div className="text-indigo-300 font-bold font-mono">{presets.styles[selectedPresetKey].dialogue_ratio}</div>
                      </div>
                    )}
                  </div>

                  {/* Negative Prompt */}
                  {presets.styles[selectedPresetKey].negative_prompt && (
                    <div className="space-y-1.5 pt-2 border-t border-slate-800">
                      <div className="text-xs font-bold text-rose-400">🚫 禁止語・ネガティブプロンプト</div>
                      <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-900/40 text-xs text-rose-200">
                        {presets.styles[selectedPresetKey].negative_prompt}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-2xl border border-slate-800 bg-[#121520] p-8 text-center text-xs text-slate-400">
                  左の一覧から文体を選択してください。
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}