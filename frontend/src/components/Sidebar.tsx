import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUserSettingsStore } from "../store/useUserSettingsStore";
import { useProjectStore, TabId } from "../store/useProjectStore";
import { useBookStore } from "../store/useBookStore";
import { useWritingStore } from "../store/useWritingStore";
import { toast } from 'sonner';

function requireBook(selectedBook: unknown, action: () => void) {
  if (!selectedBook) {
    toast.warning('最初に作品を選択してください。');
    return;
  }
  action();
}

export function Sidebar() {
  const { apiKey, setApiKey, modelType, setModelType, temperature, setTemperature } = useUserSettingsStore();
  const { activeTab, setActiveTab } = useProjectStore();
  const { selectedBook } = useBookStore();
  const { wordCount, setWordCount } = useWritingStore();
  const [tokenUsage] = useState({ calls: 0, cost: 0 });

  const navAction = (tab: TabId, needsBook = true) => () => {
    if (needsBook) {
      requireBook(selectedBook, () => setActiveTab(tab));
    } else {
      setActiveTab(tab);
    }
  };

  const tabs: { id: TabId; icon: string; label: string; needsBook: boolean }[] = [
    { id: 'landing',     icon: '🚀', label: 'ホーム',       needsBook: false },
    { id: 'books',       icon: '📚', label: '作品一覧',      needsBook: false },
    { id: 'planning',    icon: '📋', label: '企画立案',      needsBook: false },
    { id: 'plots',       icon: '📖', label: 'プロット設計',   needsBook: true },
    { id: 'write',       icon: '✍️', label: '本文執筆',      needsBook: true },
    { id: 'analytics',   icon: '📈', label: '品質＆販促',    needsBook: true },
    { id: 'style-lab',   icon: '🧬', label: '文体ラボ',      needsBook: false },
    { id: 'audit',       icon: '⚖️', label: '品質監査',      needsBook: true },
    { id: 'monitor',     icon: '📡', label: '進捗モニター',  needsBook: true },
    { id: 'strategy',    icon: '📈', label: '戦略分析',      needsBook: true },
    { id: 'import',      icon: '📥', label: 'インポート',    needsBook: true },
  ];

  return (
    <aside
      role="complementary"
      aria-label="メインナビゲーション"
      className="w-64 md:w-72 flex flex-col overflow-y-auto"
      style={{ background: 'var(--bg-sidebar)', borderRight: '1px solid var(--border)', height: '100vh' }}
    >
      {/* Header */}
      <div className="px-4 pt-5 pb-2">
        <h2 className="text-lg font-extrabold gradient-text tracking-tight">⚔️ HEGEMONY v3.0</h2>
        <p className="text-[0.7rem] text-muted-foreground font-mono mt-0.5">Novel Autogen Platform</p>
      </div>

      <div className="px-4 space-y-4 flex-1 overflow-y-auto">

        {/* ⚙️ API Key & Model */}
        <section>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">⚙️ システム設定</h3>
          <div className="bg-slate-900/90 border border-slate-700/80 rounded-lg p-3 text-xs space-y-3 shadow-sm">
            <div>
              <label htmlFor="api-key" className="block text-slate-100 font-bold text-xs mb-1">Gemini API Key</label>
              <Input
                id="api-key"
                type="password"
                placeholder="AI_KEY_..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full text-xs px-2.5 py-1.5 rounded bg-slate-950 text-white font-medium border border-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                aria-label="Gemini APIキーを入力"
              />
            </div>
            <div>
              <label htmlFor="model-select" className="block text-slate-100 font-bold text-xs mb-1">モデル</label>
              <select
                id="model-select"
                value={modelType}
                onChange={(e) => setModelType(e.target.value)}
                className="w-full text-xs px-2.5 py-1.5 rounded bg-slate-950 text-white font-medium border border-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                aria-label="使用するAIモデルを選択"
              >
                <option value="gemini-3.1-flash-lite" className="bg-slate-950 text-white">gemini-3.1-flash-lite</option>
                <option value="gemini-3.5-flash" className="bg-slate-950 text-white">gemini-3.5-flash</option>
                <option value="gemma4-31b-it" className="bg-slate-950 text-white">gemma4-31b-it</option>
                <option value="gemini-2.5-pro" className="bg-slate-950 text-white">Gemini 2.5 Pro</option>
                <option value="gemini-2.5-flash" className="bg-slate-950 text-white">Gemini 2.5 Flash</option>
                <option value="gemini-1.5-pro" className="bg-slate-950 text-white">Gemini 1.5 Pro</option>
              </select>
            </div>
          </div>
        </section>

        <hr className="border-slate-800" />

        {/* 💰 リソース状況 */}
        <section>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">💰 リソース状況</h3>
          <div className="bg-slate-900/90 border border-slate-700/80 rounded-lg p-2.5 text-xs space-y-1.5">
            <div className="flex justify-between items-center">
              <span className="text-slate-200 font-medium">API呼び出し</span>
              <span className="font-mono font-bold text-white bg-slate-800 px-1.5 py-0.5 rounded text-2xs">{tokenUsage.calls}回</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-200 font-medium">推定コスト</span>
              <span className="font-mono font-bold text-emerald-400 bg-slate-800 px-1.5 py-0.5 rounded text-2xs">${tokenUsage.cost.toFixed(4)}</span>
            </div>
          </div>
        </section>

        <hr className="border-border" />

        {/* Navigation */}
        <nav className="space-y-0.5" aria-label="アプリケーションメニュー">
          {tabs.map(({ id, icon, label, needsBook }) => (
            <Button
              key={id}
              variant={activeTab === id ? 'default' : 'secondary'}
              onClick={navAction(id, needsBook)}
              className="justify-start w-full text-xs h-9"
              aria-current={activeTab === id ? 'page' : undefined}
            >
              {icon} {label}
            </Button>
          ))}
        </nav>
      </div>

      {/* Active Selected Book Summary in Sidebar */}
      {selectedBook && (
        <div className="glass-sm animate-fade-in p-4 m-4 text-xs">
          <p className="text-muted-foreground text-2xs uppercase tracking-widest">選択中の作品</p>
          <h4 className="text-white font-bold my-0.5 truncate">{selectedBook.title}</h4>
          <span className="badge badge-purple">{selectedBook.genre}</span>
        </div>
      )}
    </aside>
  );
}