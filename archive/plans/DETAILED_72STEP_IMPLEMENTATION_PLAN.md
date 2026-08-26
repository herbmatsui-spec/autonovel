# 高優先度改善 72ステップ実装計画書

## 前提条件
- Node.js 18+ がインストール済み
- Python 3.10+ がインストール済み
- 現在のコードのバックアップを取得済み

---

## タスクA: React App.tsx リファクタリング（24ステップ）

### フェーズ1: 分析と計画（ステップ1-4）

**ステップ1: App.tsx の全体構造を分析**
- ファイル全体（906行）を読解
- 以下のセクションを識別:
  - import群（1-50行付近）
  - 型定義（Book, Plot, Chapter等）
  - コンポーネント状態（useState）
  - useEffect群
  - イベントハンドラ群
  - JSXレンダリング部分

**ステップ2: 分割対象のコンポーネントをリスト化**
- BooksListComponent（書籍一覧）
- PlotEditorComponent（プロット編集）
- ChapterWriterComponent（執筆画面）
- AnalyticsDashboardComponent（分析ダッシュボード）
- EasyModeDialog（簡単作成ダイアログ）
- ImportChapterDialog（章取り込みダイアログ）
- TaskMonitorPanel（タスク進捗監視）

**ステップ3: ディレクトリ構造を作成**
```
frontend/src/components/
├── tabs/
│   ├── BooksTab.tsx
│   ├── PlotsTab.tsx
│   ├── WriteTab.tsx
│   └── AnalyticsTab.tsx
├── dialogs/
│   ├── EasyModeDialog.tsx
│   └── ImportChapterDialog.tsx
├── panels/
│   └── TaskMonitorPanel.tsx
└── index.ts（エクスポート集約）
```

**ステップ4: 現在のApp.tsxをバックアップ**
```bash
cp frontend/src/App.tsx frontend/src/App.tsx.backup
```

### フェーズ2: 型定義の分離（ステップ5-8）

**ステップ5: types/index.ts を作成**
```typescript
// frontend/src/types/index.ts
export interface Book { ... }
export interface Plot { ... }
export interface Chapter { ... }
export interface Bible { ... }
export interface TaskStatus { ... }
// ... その他全型定義を移動
```

**ステップ6: App.tsx から型定義を削除**
- ステップ5で作成したtypes/index.tsからimportに変更
- ローカル定義を削除

**ステップ7: 型定義のエクスポート確認**
```typescript
// frontend/src/types/index.ts
export * from './api';
```

**ステップ8: 型整合性チェック**
```bash
cd frontend && npx tsc --noEmit
```

### フェーズ3: Custom Hooks の抽出（ステップ9-12）

**ステップ9: hooks/useTaskStream.ts を作成**
```typescript
// frontend/src/hooks/useTaskStream.ts
export function useTaskStream(taskId: string | null, callbacks: {...}) {
  // SSE接続ロジックを抽出
  // クリーンアップ処理 포함
}
```

**ステップ10: hooks/useBookDetails.ts を作成**
```typescript
// frontend/src/hooks/useBookDetails.ts
export function useBookDetails(bookId: number | null, activeTab: string) {
  // loadBookDetails ロジックを抽出
  // plots, chapters, bible等の状態管理
}
```

**ステップ11: hooks/useTaskMonitor.ts を作成**
```typescript
// frontend/src/hooks/useTaskMonitor.ts
export function useTaskMonitor() {
  // activeTaskId, taskStatus状態
  // handleStopTask関数
  // ログ自動スクロールロジック
}
```

**ステップ12: hooks/index.ts を作成してエクスポート**
```typescript
export * from './useBooks';
export * from './useTaskStream';
export * from './useBookDetails';
export * from './useTaskMonitor';
```

### フェーズ4: Dialog コンポーネントの作成（ステップ13-16）

**ステップ13: dialogs/EasyModeDialog.tsx を作成**
```typescript
// frontend/src/components/dialogs/EasyModeDialog.tsx
interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: EasyModeParams) => void;
}
export function EasyModeDialog({ isOpen, onClose, onSubmit }: Props) {
  // easyGenre, easyKeywords, easyArchetype, easyTargetEps, easyWordCount状態
  // フォームJSX
}
```

**ステップ14: dialogs/ImportChapterDialog.tsx を作成**
```typescript
// frontend/src/components/dialogs/ImportChapterDialog.tsx
interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (epNum: number, text: string, doRefine: boolean) => void;
}
export function ImportChapterDialog({ isOpen, onClose, onSubmit }: Props) {
  // importEpNum, importText, importDoRefine状態
  // フォームJSX
}
```

**ステップ15: dialogs/index.ts を作成**
```typescript
export { EasyModeDialog } from './EasyModeDialog';
export { ImportChapterDialog } from './ImportChapterDialog';
```

**ステップ16: Dialog 表示ロジックを確認**
- App.tsx内のshowCreateModal, showImportModal状態をpropsとして渡すよう変更

### フェーズ5: Tab コンポーネントの作成（ステップ17-20）

**ステップ17: tabs/BooksTab.tsx を作成**
```typescript
// frontend/src/components/tabs/BooksTab.tsx
export function BooksTab({ books, selectedBook, onSelect, onDelete }) {
  // 書籍一覧表示ロジック
  // 新規作成ボタン
}
```

**ステップ18: tabs/PlotsTab.tsx を作成**
```typescript
// frontend/src/components/tabs/PlotsTab.tsx
export function PlotsTab({ plots, bookId, onExpand, onRebuild }) {
  // プロット一覧・編集ロジック
}
```

**ステップ19: tabs/WriteTab.tsx を作成**
```typescript
// frontend/src/components/tabs/WriteTab.tsx
export function WriteTab({ chapters, bible, bookId, onGenerate, onImport }) {
  // 章一覧・執筆ロジック
}
```

**ステップ20: tabs/AnalyticsTab.tsx を作成**
```typescript
// frontend/src/components/tabs/AnalyticsTab.tsx
export function AnalyticsTab({ optHistory, pendingPatches, promptVersions, metricTrend }) {
  // 分析ダッシュボード表示ロジック
}
```

### フェーズ6: App.tsx の再構成（ステップ21-24）

**ステップ21: App.tsx を簡略化**
```typescript
// 新しいApp.tsx
import { BooksTab } from './components/tabs/BooksTab';
import { PlotsTab } from './components/tabs/PlotsTab';
import { WriteTab } from './components/tabs/WriteTab';
import { AnalyticsTab } from './components/tabs/AnalyticsTab';
import { EasyModeDialog } from './components/dialogs/EasyModeDialog';
import { ImportChapterDialog } from './components/dialogs/ImportChapterDialog';
import { useBooks } from './hooks/useBooks';
import { useTaskStream } from './hooks/useTaskStream';

export default function App() {
  // 最小限の状態のみ保持
  const { books, selectedBook, setSelectedBook } = useBooks();
  const { activeTaskId, taskStatus } = useTaskStream(...);
  
  // renderContent() でタブ切り替え
  return (
    <div>
      <Sidebar />
      {activeTaskId && <TaskMonitorPanel />}
      {renderContent()}
      <EasyModeDialog />
      <ImportChapterDialog />
    </div>
  );
}
```

**ステップ22: 残存ロジックをhooks/componentsに移動**
- ステップ21で.App.tsxに残ったロジックを適切なhooks/componentsに移動

**ステップ23: ビルド確認**
```bash
cd frontend && npm run build
```

**ステップ24: 動作確認**
```bash
cd frontend && npm run dev
# ブラウザで http://localhost:5173 を確認
```

---

## タスクB: CORS設定の制限（24ステップ）

### フェーズ1: 現在のCORS設定を確認（ステップ25-28）

**ステップ25: server.py のCORS設定を確認**
```python
# src/backend/server.py:91-97
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # これが問題
    ...
)
```

**ステップ26: 環境変数設定ファイルを確認**
```bash
# .env または config/ ディレクトリを確認
# 既存の環境変数管理模式を調査
```

**ステップ27: 許可すべきoriginをリスト化**
- 開発環境: http://localhost:5173 (React), http://localhost:8501 (Streamlit)
- 本番環境: 本番ドメイン

**ステップ28: 設定ファイルのバックアップ**
```bash
cp config/settings.py config/settings.py.backup
```

### フェーズ2: 環境変数サポートの実装（ステップ29-36）

**ステップ29: config/cors_config.py を作成**
```python
# config/cors_config.py
import os
from typing import List

def get_allowed_origins() -> List[str]:
    """環境変数からCORS許可originリストを取得"""
    origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not origins_env:
        # デフォルトは空（全て拒否）または開発用
        return ["http://localhost:5173", "http://localhost:8501"]
    return [o.strip() for o in origins_env.split(",") if o.strip()]
```

**ステップ30: config/settings.py にCORS設定を追加**
```python
# config/settings.py
class Settings(BaseSettings):
    # 既存設定...
    cors_allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:8501"]
    
    class Config:
        env_file = ".env"
```

**ステップ31: .env.example を作成**
```bash
# .env.example
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8501
# 本番環境では以下のように設定
# CORS_ALLOWED_ORIGINS=https://your-production-domain.com
```

**ステップ32: .gitignore に.env を追加確認**
```
# .gitignore
.env
```

**ステップ33: 設定読み込みテストを作成**
```python
# tests/test_cors_config.py
def test_get_allowed_origins_from_env():
    import os
    os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://localhost:3000" in origins
    assert "http://localhost:8000" in origins
```

**ステップ34: 設定テストを実行**
```bash
cd /i:/R15/cR15 && python -m pytest tests/test_cors_config.py -v
```

**ステップ35: 設定ファイルの変更をドキュメント化**
```markdown
<!-- docs/CORS_CONFIG.md -->
# CORS設定ガイド
## 環境変数
CORS_ALLOWED_ORIGINS: カンマ区切りで許可originリスト
```

**ステップ36: 既存テストのCORS関連を確認**
```bash
grep -r "allow_origins" tests/
```

### フェーズ3: server.py の更新（ステップ37-44）

**ステップ37: server.py にCORS設定インポートを追加**
```python
# src/backend/server.py の先頭付近
from config.cors_config import get_allowed_origins
```

**ステップ38: CORS middleware を動的に更新**
```python
# src/backend/server.py
# lifespan 関数の前に追加
def configure_cors(app: FastAPI):
    allowed_origins = get_allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

**ステップ39: lifespan 内で configure_cors を呼び出し**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB初期化...
    configure_cors(app)  # 追加
    yield
    # シャットダウン...
```

**ステップ40: 開発環境で動作確認**
```bash
# ターミナル1: バックエンド起動
cd /i:/R15/cR15 && python -m uvicorn src.backend.server:app --reload

# ターミナル2: curlでCORSヘッダー確認
curl -I -X OPTIONS http://localhost:8000/health \
  -H "Origin: http://localhost:5173"
# Access-Control-Allow-Origin が設定されていることを確認
```

**ステップ41: 本番環境想定でテスト**
```bash
# 許可されていないoriginからのリクエストをテスト
curl -I -X OPTIONS http://localhost:8000/health \
  -H "Origin: http://malicious-site.com"
# Access-Control-Allow-Origin が設定されていないことを確認
```

**ステップ42: ログ出力の追加**
```python
# configure_cors 関数に追加
logger.info(f"CORS allowed origins: {allowed_origins}")
```

**ステップ43: エンドポイントテストを更新**
```python
# tests/test_cors_endpoints.py
def test_cors_headers_in_response():
    response = client.get("/health")
    assert "Access-Control-Allow-Origin" in response.headers
```

**ステップ44: 全テストを実行**
```bash
cd /i:/R15/cR15 && python -m pytest tests/ -v --tb=short
```

### フェーズ4: ドキュメントとデプロイ対応（ステップ45-48）

**ステップ45: docker-compose.yml の更新**
```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
```

**ステップ46: Dockerfile の確認**
```dockerfile
# Dockerfile
ENV CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8501
```

**ステップ47: デプロイ手順書を更新**
```markdown
<!-- docs/DEPLOY.md -->
## CORS設定
本番デプロイ時は以下のように環境変数を設定:
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

**ステップ48: 最終確認**
```bash
# セキュリティチェックリスト
- [x] allow_origins=["*"] を削除
- [x] 環境変数でoriginを指定可能
- [x] デフォルトは開発用localhostのみ
- [x] ログで許可originを確認可能
```

---

## タスクC: Streamlit状態管理の統一（24ステップ）

### フェーズ1: 現在の状態管理の分析（ステップ49-52）

**ステップ49: streamlit_app/state.py を分析**
```python
# UIStateStore の構造を確認
# 哪些プロパティがあるか調査
class UIStateStore:
    runtime: RuntimeState  # app_mode, token_stats等
    # その他状態
```

**ステップ50: st.session_state の使用箇所を調査**
```bash
grep -r "st.session_state" streamlit_app/
```

**ステップ51: 状態使用パターンを分類**
- 永続化必要（localStorage/DB同期）: apiKey, selectedBookId
- 一時的（画面遷移で破棄OK）: UI表示状態

**ステップ52: バックアップ取得**
```bash
cp streamlit_app/state.py streamlit_app/state.py.backup
cp streamlit_app/app.py streamlit_app/app.py.backup
```

### フェーズ2: UIStateStore の強化（ステップ53-60）

**ステップ53: streamlit_app/state.py に新しい状態クラスを追加**
```python
# streamlit_app/state.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class UIState:
    """Streamlit画面状態（UIStateStoreで管理）"""
    # ダイアログ表示状態
    show_create_modal: bool = False
    show_import_modal: bool = False
    
    # フォーム状態
    easy_genre: str = 'ダークファンタジー'
    easy_keywords: str = '追放, 復讐, システムハック'
    easy_archetype: str = 'avenger'
    easy_target_eps: int = 10
    easy_word_count: int = 3000
    easy_concept: str = ''
    
    import_ep_num: int = 1
    import_text: str = ''
    import_do_refine: bool = True
    
    # 執筆設定
    write_from: int = 1
    write_to: int = 5
    write_passion: float = 0.85
```

**ステップ54: UIStateStore に状態アクセス用プロパティを追加**
```python
# streamlit_app/state.py
class UIStateStore:
    # 既存コード...
    
    @property
    def ui_state(self) -> UIState:
        return self._ui_state
    
    def update_ui_state(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._ui_state, key):
                setattr(self._ui_state, key, value)
```

**ステップ55: Streamlitコンポーネント用ヘルパーを追加**
```python
# streamlit_app/state.py
def get_ui_state() -> UIState:
    """現在のUI状態を返す（Streamlitコンポーネント内から呼び出し）"""
    return UIStateStore.get_runtime().ui_state

def update_ui_state(**kwargs):
    """UI状態を更新"""
    UIStateStore.get_runtime().update_ui_state(**kwargs)
```

**ステップ56: st.session_state からの移行ヘルパーを作成**
```python
# streamlit_app/state.py
def migrate_from_session(key: str, default: Any = None) -> Any:
    """st.session_state から値を取得してUIStateStoreに移行"""
    if key in st.session_state:
        value = st.session_state[key]
        del st.session_state[key]  # 移行後に削除
        return value
    return default
```

**ステップ57: 初期化処理を更新**
```python
# streamlit_app/app.py の _init_session 関数
def _init_session() -> None:
    runtime = UIStateStore.get_runtime()
    
    # 既存の設定...
    
    # 新しいUI状態の必要初期値
    if runtime.ui_state is None:
        runtime.ui_state = UIState()
```

**ステップ58: 状態変更サブスクリプションを確認**
```python
# streamlit_app/app.py
UIStateStore.subscribe("active_job", lambda job: st.toast(...))
# 必要に応じて ui_state 変更時のサブスクライバも追加
```

**ステップ59: 型定義ファイルを確認**
```python
# streamlit_app/state_keys.py
# 状態キー定数を管理（もし存在すれば）
```

**ステップ60: テストファイルを作成**
```python
# tests/test_ui_state_store.py
def test_ui_state_initialization():
    from streamlit_app.state import UIStateStore, UIState
    runtime = UIStateStore.get_runtime()
    assert isinstance(runtime.ui_state, UIState)
    assert runtime.ui_state.show_create_modal == False
```

### フェーズ3: コンポーネントの移行（ステップ61-68）

**ステップ61: streamlit_app/ui_tabs_writing.py を修正**
```python
# 修正前
if 'import_ep_num' not in st.session_state:
    st.session_state.import_ep_num = 1

# 修正後
from streamlit_app.state import get_ui_state, update_ui_state
ui_state = get_ui_state()
```

**ステップ62: streamlit_app/ui_tabs_writing.py のフォーム更新**
```python
# 修正後
import_ep_num = st.number_input(
    "エピソード番号",
    min_value=1,
    value=get_ui_state().import_ep_num,
    key="import_ep_num_input"
)
if import_ep_num != get_ui_state().import_ep_num:
    update_ui_state(import_ep_num=import_ep_num)
```

**ステップ63: streamlit_app/ui_tabs_planning.py を修正**
```python
# easy mode 関連の状態を移行
from streamlit_app.state import get_ui_state, update_ui_state

easy_genre = st.selectbox(
    "ジャンル",
    options=['ダークファンタジー', '恋愛ファンタジー', ...],
    index=['ダークファンタジー', ...].index(get_ui_state().easy_genre)
)
```

**ステップ64: streamlit_app/sidebar.py を修正**
```python
# APIキー管理等、st.session_state を使用している箇所を確認・移行
from streamlit_app.state import UIStateStore

runtime = UIStateStore.get_runtime()
# runtime.api_key 等を使用
```

**ステップ65: streamlit_app/progress.py を修正**
```python
# 進捗表示の状態管理を確認
# st.session_state を使用していなければスキップ
```

**ステップ66: streamlit_app/ui_tabs_analytics.py を修正**
```python
# 分析タブの状態管理を確認・移行
```

**ステップ67: streamlit_app/ui_tabs_monitor.py を修正**
```python
# 監視タブの状態管理を確認・移行
```

**ステップ68: streamlit_app/ui_tabs_audit.py を修正**
```python
# 監査タブの状態管理を確認・移行
```

### フェーズ4: 統合テストと確認（ステップ69-72）

**ステップ69: Streamlitアプリ起動テスト**
```bash
cd /i:/R15/cR15
streamlit run streamlit_app/app.py --server.headless true
# エラーがないことを確認
```

**ステップ70: 状態遷移テスト**
```python
# tests/test_streamlit_state.py
def test_state_persistence_across_reruns():
    """Streamlit rerun間で状態が保持されることを確認"""
    # UIStateStore.subscribe を使ったテスト
```

**ステップ71: メモリリークチェック**
```python
# tests/test_streamlit_state.py
def test_no_memory_leak():
    """サブスクリプションが蓄積しないことを確認"""
    initial_count = len(UIStateStore._subscribers)
    for _ in range(100):
        UIStateStore.subscribe("test_key", lambda x: x)
    # クリーンアップ処理が正しく動くか確認
```

**ステップ72: 最終動作確認チェックリスト**
```
- [ ] Streamlitアプリがエラーなく起動
- [ ] サイドバーのAPIキー入力→保持が正常
- [ ] Easy Mode ダイアログの表示/非表示が正常
- [ ] 章取り込みダイアログの表示/非表示が正常
- [ ] 執筆設定（write_from, write_to等）が保持される
- [ ] ページ遷移後に状態が保持される
- [ ] st.session_state の使用箇所が0件
```

---

## 72ステップ総括

| フェーズ | ステップ範囲 | 主要タスク |
|---------|-------------|-----------|
| 分析・計画 | 1-4, 25-28, 49-52 | コード分析・バックアップ |
| 型定義分離 | 5-8 | TypeScript型定義の分離 |
| Hooks抽出 | 9-12 | Custom Hooks作成 |
| Dialog作成 | 13-16 | React Dialog компонент |
| Tab作成 | 17-20 | React Tab компонент |
| App再構成 | 21-24 | App.tsx簡略化 |
| CORS設定 | 29-48 | 環境変数対応・server.py更新 |
| State移行 | 53-68 | UIStateStore強化・ компонент更新 |
| 統合テスト | 24, 44, 69-72 | 動作確認・テスト実行 |

## 次のステップ
1. ステップ1-4から順番に実行
2. 各フェーズ完了後にテストを実行
3. 問題があればその場で修正
4. 全ステップ完了後、バックアップファイルを削除