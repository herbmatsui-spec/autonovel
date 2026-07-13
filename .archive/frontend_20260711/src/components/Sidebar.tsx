import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Book } from "../api";
import { useUserSettingsStore } from "../store/useUserSettingsStore";
import { useProjectStore } from "../store/useProjectStore";
import { toast } from 'sonner';

export function Sidebar() {
  const { apiKey, setApiKey, modelType, setModelType } = useUserSettingsStore();
  const { activeTab, setActiveTab, selectedBook } = useProjectStore();

  return (
    <aside
      role="complementary"
      aria-label="メインナビゲーション"
      className="w-64 md:w-72 p-4 md:p-6 flex flex-col"
      style={{ background: 'var(--bg-sidebar)', borderRight: '1px solid var(--border)' }}
    >
      <div style={{ marginBottom: '2.5rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.03em' }} className="gradient-text">
          ⚔️ HEGEMONY v3.0
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.25rem', fontFamily: 'var(--font-mono)' }}>
          Novel Autogen Platform
        </p>
      </div>

      {/* Global Key Settings */}
      <div className="glass-panel" style={{ padding: '1rem', marginBottom: '2rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
        <div>
          <label htmlFor="api-key" style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.25rem', fontWeight: 'bold' }}>Gemini API Key</label>
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
          <label htmlFor="model-select" style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.25rem', fontWeight: 'bold' }}>モデル</label>
          <select
            id="model-select"
            value={modelType}
            onChange={(e) => setModelType(e.target.value)}
            style={{ fontSize: '0.8rem', padding: '0.5rem', width: '100%' }}
            aria-label="使用するAIモデルを選択"
          >
            <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
            <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
          </select>
        </div>
      </div>

      {/* Tab Buttons */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1' }} aria-label="アプリケーションメニュー">
        <Button
          variant={activeTab === 'books' ? 'default' : 'secondary'}
          onClick={() => setActiveTab('books')}
          className="justify-start w-full"
          aria-current={activeTab === 'books' ? 'page' : undefined}
          aria-label="作品一覧ページへ"
        >
          📚 作品一覧
        </Button>
        <Button
          variant={activeTab === 'plots' ? 'default' : 'secondary'}
          onClick={() => {
            if (!selectedBook) {
              toast.warning('最初に作品を選択してください。');
              return;
            }
            setActiveTab('plots');
          }}
          className="justify-start w-full"
          aria-current={activeTab === 'plots' ? 'page' : undefined}
          aria-label="プロット設計ページへ"
        >
          🗺️ プロット設計
        </Button>
        <Button
          variant={activeTab === 'write' ? 'default' : 'secondary'}
          onClick={() => {
            if (!selectedBook) {
              toast.warning('最初に作品を選択してください。');
              return;
            }
            setActiveTab('write');
          }}
          className="justify-start w-full"
          aria-current={activeTab === 'write' ? 'page' : undefined}
          aria-label="エピソード執筆ページへ"
        >
          ✍️ エピソード執筆
        </Button>
        <Button
          variant={activeTab === 'analytics' ? 'default' : 'secondary'}
          onClick={() => {
            if (!selectedBook) {
              toast.warning('最初に作品を選択してください。');
              return;
            }
            setActiveTab('analytics');
          }}
          className="justify-start w-full"
          aria-current={activeTab === 'analytics' ? 'page' : undefined}
          aria-label="品質および販促分析ページへ"
        >
          📈 品質＆販促
        </Button>
      </nav>

      {/* Active Selected Book Summary in Sidebar */}
      {selectedBook && (
        <div className="glass-panel animate-fade-in" style={{ padding: '1rem', marginTop: 'auto', fontSize: '0.85rem' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>選択中の作品</p>
          <h4 style={{ color: '#ffffff', margin: '0.25rem 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {selectedBook.title}
          </h4>
          <span className="badge badge-purple">{selectedBook.genre}</span>
        </div>
      )}
    </aside>
  );
}
