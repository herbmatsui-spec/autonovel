import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUserSettingsStore } from "../store/useUserSettingsStore";
import { useProjectStore } from "../store/useProjectStore";
import { useBookStore } from "../store/useBookStore";
import { useWritingStore } from "../store/useWritingStore";
import { toast } from 'sonner';
import { getBooks, checkBackendHealth } from "../api";

type TabId = 'landing' | 'books' | 'plots' | 'write' | 'analytics' | 'planning' | 'style-lab' | 'audit' | 'monitor' | 'strategy' | 'import';

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
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
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
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">⚙️ システム設定</h3>
          <div className="space-y-2 glass-panel p-3 text-xs">
            <div>
              <label htmlFor="api-key" className="block text-muted-foreground mb-0.5 font-semibold text-xs">Gemini API Key</label>
              <Input
                id="api-key"
                type="password"
                placeholder="AI_KEY_..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                aria-label="Gemini APIキーを入力"
              />
            </div>
            <div>
              <label htmlFor="model-select" className="block text-muted-foreground mb-0.5 font-semibold text-xs">モデル</label>
              <select
                id="model-select"
                value={modelType}
                onChange={(e) => setModelType(e.target.value)}
                className="w-full text-xs p-1.5 rounded bg-background border border-border"
                aria-label="使用するAIモデルを選択"
              >
                <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              </select>
            </div>
          </div>
        </section>

        <hr className="border-border" />

        {/* 🎮 操作モード */}
        <section>
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">🎮 操作モード</h3>
          <div className="glass-sm p-2 text-xs">
            <p className="text-muted-foreground">上級者モード（全機能）</p>
          </div>
        </section>

        <hr className="border-border" />

        {/* 🛠️ 執筆パラメータ */}
        <section>
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">🛠️ 執筆パラメータ</h3>
          <div className="space-y-2 glass-sm p-2 text-xs">
            <div>
              <label htmlFor="word-count" className="block text-muted-foreground mb-0.5 font-semibold">目標文字数/話</label>
              <input
                id="word-count"
                type="number"
                min={1000}
                max={5000}
                step={100}
                value={wordCount}
                onChange={(e) => setWordCount(Number(e.target.value))}
                className="w-full text-xs p-1.5 rounded bg-background border border-border"
              />
            </div>
            <div>
              <label htmlFor="temperature" className="block text-muted-foreground mb-0.5 font-semibold">Temperature</label>
              <input
                id="temperature"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
                className="w-full"
              />
              <span className="text-xs text-muted-foreground">{temperature.toFixed(2)}</span>
            </div>
          </div>
        </section>

        <hr className="border-border" />

        {/* 💰 リソース状況 */}
        <section>
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">💰 リソース状況</h3>
          <div className="glass-sm p-2 text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">API呼び出し</span>
              <span className="font-mono font-semibold">{tokenUsage.calls}回</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">推定コスト</span>
              <span className="font-mono font-semibold">${tokenUsage.cost.toFixed(4)}</span>
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