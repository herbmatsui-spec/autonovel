import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUserSettingsStore } from "../store/useUserSettingsStore";
import type { TabId } from "../store/useProjectStore";
import { useBookStore } from "../store/useBookStore";
import { useUIStore } from "../store/useUIStore";
import { useNavigate, useLocation } from 'react-router-dom';

import { toast } from 'sonner';

function requireBook(selectedBook: unknown, action: () => void) {
  if (!selectedBook) {
    toast.warning('最初に作品を選択してください。');
    return;
  }
  action();
}

export function Sidebar() {
  const { apiKey, setApiKey, modelType, setModelType, isExpertMode, setIsExpertMode } = useUserSettingsStore();
  const { selectedBook } = useBookStore();
  const setCreateModalOpen = useUIStore((s) => s.setCreateModalOpen);
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname; // e.g., "/books"
  // Remove leading slash and any trailing slash
  const activeTabId = pathname.replace(/^\/|\/$/g, '') as TabId | '';
  // If empty, default to landing
  const currentTab = activeTabId || 'landing';

  const navAction = (tab: TabId, needsBook = true) => () => {
    if (needsBook) {
      requireBook(selectedBook, () => navigate(`/${tab}`));
    } else {
      navigate(`/${tab}`);
    }
  };

  const allTabs = [
    { id: 'landing',     icon: '🚀', label: 'ホーム',       needsBook: false, expertOnly: false },
    { id: 'books',       icon: '📚', label: '作品一覧',      needsBook: false, expertOnly: false },
    { id: 'planning',    icon: '📋', label: '企画立案',      needsBook: false, expertOnly: true },
    { id: 'plots',       icon: '📖', label: 'プロット設計',   needsBook: true,  expertOnly: true },
    { id: 'write',       icon: '✍️', label: '本文執筆',      needsBook: true,  expertOnly: false },
    { id: 'analytics',   icon: '📈', label: '品質＆販促',    needsBook: true,  expertOnly: true },
    { id: 'style-lab',   icon: '🧬', label: '文体ラボ',      needsBook: false, expertOnly: true },
    { id: 'audit',       icon: '⚖️', label: '品質監査',      needsBook: true,  expertOnly: true },
    { id: 'monitor',     icon: '📡', label: '進捗モニター',  needsBook: true,  expertOnly: true },
    { id: 'strategy',    icon: '📈', label: '戦略分析',      needsBook: true,  expertOnly: true },
    { id: 'import',      icon: '📥', label: 'インポート',    needsBook: true,  expertOnly: true },
  ] as const;

  const tabs = allTabs.filter(t => isExpertMode || !t.expertOnly);

  return (
    <aside className="flex-shrink-0 w-[250px] bg-[var(--bg-sidebar)] text-[var(--text-sidebar)] border-r border-[var(--border)] p-4">
      <div className="flex items-center space-x-3 mb-6">
        <div className="h-8 w-8 bg-[var(--accent)] rounded-full flex items-center justify-center">
          <span className="text-white font-bold">🎌</span>
        </div>
        <h1 className="text-xl font-bold">AutoNovel</h1>
      </div>
      <nav className="space-y-2">
        {tabs.map(({ id, icon, label }) => (
          <Button
            key={id}
            variant={currentTab === id ? 'destructive' : 'secondary'}
            className="w-full text-left justify-start"
            onClick={navAction(id, /* needsBook */ ['plots','write','analytics','audit','monitor','strategy','import'].includes(id))}
          >
            <div className="flex items-center space-x-3">
              <span>{icon}</span>
              <span className="hidden md:inline">{label}</span>
            </div>
          </Button>
        ))}
      </nav>
      <div className="mt-6 pt-4 border-t border-[var(--border)]">
        <h2 className="font-semibold mb-2">設定</h2>
        <Button
          variant="ghost"
          className="w-full text-left justify-start mb-2"
          onClick={() => setIsExpertMode(!isExpertMode)}
        >
          <div className="flex items-center space-x-3">
            <span>⚙️</span>
            <span className="hidden md:inline">エキスパートモード: {isExpertMode ? 'ON' : 'OFF'}</span>
          </div>
        </Button>
        <Button
          variant="ghost"
          className="w-full text-left justify-start mb-2"
          onClick={() => setCreateModalOpen(true)}
        >
          <div className="flex items-center space-x-3">
            <span>📝</span>
            <span className="hidden md:inline">新規作成</span>
          </div>
        </Button>
        <div className="space-y-1">
          <label className="text-xs block mb-1">APIキー</label>
          <Input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-..."
            className="w-full"
          />
        </div>
        <div className="space-y-1 mt-2">
          <label className="text-xs block mb-1">モデルタイプ</label>
          <Button
            variant="ghost"
            className="w-full text-left justify-start"
            onClick={() => setModelType(modelType === 'openai' ? 'gemini' : 'openai')}
          >
            <span className="hidden md:inline">現在のモデル: {modelType === 'openai' ? 'OpenAI' : 'Gemini'}</span>
            <span className="ml-2">{modelType === 'openai' ? '🔄' : '🔄'}</span>
          </Button>
        </div>
      </div>
    </aside>
  );
}