# Streamlit → React 完全移行 72ステップ実装計画書

**前提:**
- ADR-0003「Streamlit共存・廃止方針」に準拠
- 低性能LLMでも実装可能な小さなステップに分割
- バックアップ取得後に実行すること

---

## Phase 0: 分析・準備（ステップ1-12）

### グループA: コード分析とバックアップ（ステップ1-6）

**ステップ1: Streamlitアプリ全体ファイル一覧を取得**
```bash
cd autonovel && python -c "import os; [print(f) for f in __import__('glob').glob('streamlit_app/**/*.py', recursive=True)]"
```
出力ファイル: `plans/inventory_streamlit.txt`

**ステップ2: Reactアプリ全体ファイル一覧を取得**
```bash
cd autonovel && python -c "import os; [print(f) for f in __import__('glob').glob('frontend/src/**/*', recursive=True) if f.endswith(('.ts', '.tsx'))]"
```
出力ファイル: `plans/inventory_react.txt`

**ステップ3: Streamlitの状態管理ファイルを分析**
```python
# streamlit_app/state.py の主要クラスをリスト化
# - UIStateStore
# - SessionManager
# - BaseStore, JobStore, PollStateStore, ToastStore, SessionStore
```

**ステップ4: StreamlitのUIタブファイルを分析**
```bash
ls streamlit_app/ui_tabs_*.py
# 対象ファイル:
# - ui_tabs_writing.py
# - ui_tabs_planning.py
# - ui_tabs_analytics.py
# - ui_tabs_audit.py
# - ui_tabs_monitor.py
# - ui_tabs_marketing.py
# - ui_tabs_writing_helpers.py
```

**ステップ5: バックアップを取得**
```bash
cd autonovel
mkdir -p backup/streamlit_app_backup
cp -r streamlit_app/* backup/streamlit_app_backup/
cp -r frontend/src backup/frontend_src_backup/
```

**ステップ6: APIエンドポイント対応表を作成**
Streamlit(api_client.py) と React(api.ts) の両方のAPI呼び出しを照合:
```
/api/books           → getBooks()
/api/books/{id}      → getBook()
/api/plots/{id}      → getPlots()
/api/chapters/{id}   → getChapters()
/api/bibles/{id}     → getBible()
/api/tasks/{id}/stream → connectTaskStream()
/api/easy_mode/generate → generateEasy()
...
```

### グループB: React基盤確認（ステップ7-12）

**ステップ7: React APIクライアントを確認**
ファイル: `frontend/src/api.ts`
- 既存:endpoints確認
- 不足:endpointsをリスト化

**ステップ8: React Hooksを確認**
ファイル: `frontend/src/hooks/`
- useBooks.ts
- useTaskStream.ts
- useBookDetails.ts
- useTaskMonitor.ts
- useAppActions.ts

**ステップ9: React Storesを確認**
ファイル: `frontend/src/store/`
- useBookStore.ts
- useUIStore.ts
- useTaskStore.ts
- useWritingStore.ts
- useEasyModeStore.ts
- useUserSettingsStore.ts
- useProjectStore.ts

**ステップ10: Reactコンポーネントを確認**
ファイル: `frontend/src/components/`
- tabs/: BooksTab, PlotsTab, WriteTab, AnalyticsTab等
- dialogs/: EasyModeDialog, ImportChapterDialog
- panels/: TaskMonitor
- ui/: 共通UIコンポーネント群

**ステップ11: バックエンドAPI server.pyを確認**
```python
# src/backend/server.py の router 定義を確認
# API_PREFIX = "/api"
```

**ステップ12: 移行優先度マトリクスを作成**
```
高優先度: BooksTab, WriteTab, タスク監視, API連携
中優先度: PlotsTab, AnalyticsTab, PlanningTab
低優先度: AuditTab, StyleLabTab, Marketing機能
```

---

## Phase 1: Reactへの移行（ステップ13-48）

### グループC: EasyMode/EzStudio機能（ステップ13-18）

**ステップ13: React EasyModeDialogを確認**
ファイル: `frontend/src/components/dialogs/EasyModeDialog.tsx`
現状: 存在確認済み

**ステップ14: Streamlit EasyMode実装を検索**
```bash
grep -r "easy_mode\|EasyMode\|ez_studio" streamlit_app/
```
主なファイル:
- ui_tabs_planning.py（generate_plan呼び出し）
- state.py（easy_genre管理等）

**ステップ15: React generateEasy API呼び出しを確認**
```typescript
// frontend/src/api.ts
export async function generateEasy(params: EasyModeParams): Promise<string>
```

**ステップ16: Streamlitのgenerate_plan actionsを確認**
```python
# streamlit_app/actions.py
def generate_plan(engine: Any, params: Dict[str, Any]) -> Any:
```

**ステップ17: EasyMode Hook/Store実装を確認**
```typescript
// frontend/src/store/useEasyModeStore.ts
// frontend/src/hooks/useAppActions.ts - handleCreateEasyMode
```

**ステップ18: EasyMode機能整合性テスト**
```bash
cd frontend && npm run build
```
確認: EasyModeDialog + generateEasy API連携

### グループD: BooksTab/作品管理機能（ステップ19-24）

**ステップ19: React BooksTabを確認**
ファイル: `frontend/src/components/tabs/BooksTab.tsx`

**ステップ20: Streamlit書籍管理機能を検索**
```bash
grep -r "book\|Books" streamlit_app/ --include="*.py" -l
```
主なファイル: sidebar_sections/book_manager.py, api_client.py

**ステップ21: Streamlit book_manager内容を確認**
```python
# streamlit_app/sidebar_sections/book_manager.py
# 新規作成、削除、選択等功能
```

**ステップ22: React API書籍操作を確認**
```typescript
// frontend/src/api.ts
getBooks(), getBook(), deleteBook()
```

**ステップ23: useBooks Hookを確認**
```typescript
// frontend/src/hooks/useBooks.ts
// 書籍一覧取得・削除ロジック
```

**ステップ24: BooksTabとAPI連携テスト**
- React: BooksTab → useBooks() → getBooks()
- Streamlit: sidebar → api_client.list_books()
- 差分: 機能同等確認

### グループE: 章管理/WriteTab機能（ステップ25-30）

**ステップ25: React WriteTabを確認**
ファイル: `frontend/src/components/tabs/WriteTab.tsx`

**ステップ26: Streamlit章管理機能を検索**
```bash
grep -r "chapter\|Episode" streamlit_app/ --include="*.py" -l
```
主なファイル: ui_tabs_writing.py, api_client.py

**ステップ27: React API章操作を確認**
```typescript
// frontend/src/api.ts
getChapters(), importChapter(), generateEpisodes()
```

**ステップ28: Streamlit章執筆UIを確認**
```python
# streamlit_app/ui_tabs_writing.py
# 章一覧、執筆フォーム、取り込みフォーム
```

**ステップ29: WriteTabとuseWritingStoreを確認**
```typescript
// frontend/src/store/useWritingStore.ts
// writeFrom, writeTo, writePassion, importEpNum等
```

**ステップ30: 章管理機能整合性テスト**
- React: WriteTab → getChapters() → 章一覧表示
- Streamlit: ui_tabs_writing → get_episodes() → 章一覧表示
- 機能同等確認

### グループF: プロット/PlotsTab機能（ステップ31-36）

**ステップ31: React PlotsTabを確認**
ファイル: `frontend/src/components/tabs/PlotsTab.tsx`

**ステップ32: Streamlitプロット管理機能を検索**
```bash
grep -r "plot" streamlit_app/ --include="*.py" -l
```

**ステップ33: React APIプロット操作を確認**
```typescript
// frontend/src/api.ts
getPlots(), expandPlots(), rebuildPlots(), planGeneration()
```

**ステップ34: Streamlit ui_tabs_planning.pyを確認**
```python
# プロット編集・拡張・Rebuild機能
```

**ステップ35: PlotsTabとuseBookStore/plots stateを確認**
```typescript
// frontend/src/store/useBookStore.ts
// plots: Plot[]
```

**ステップ36: プロット機能整合性テスト**
- React: PlotsTab → getPlots() → プロット一覧表示
- Streamlit: 同一機能比較

### グループG: タスク監視/TaskMonitor機能（ステップ37-42）

**ステップ37: React TaskMonitorを確認**
ファイル: `frontend/src/components/panels/TaskMonitor.tsx`

**ステップ38: Streamlitタスク監視機能を検索**
```bash
grep -r "task\|monitor\|background" streamlit_app/ --include="*.py" -l
```
主なファイル: ui_tabs_monitor.py, background.py, progress.py

**ステップ39: React APIタスク操作を確認**
```typescript
// frontend/src/api.ts
connectTaskStream(), getTaskStatus(), stopTask()
```

**ステップ40: useTaskStream Hookを確認**
```typescript
// frontend/src/hooks/useTaskStream.ts
// SSE接続・タスク状態管理
```

**ステップ41: Streamlitタスク状態管理を確認**
```python
# streamlit_app/state.py - JobStore
# streamlit_app/stores/job_store.py
```

**ステップ42: タスク監視機能整合性テスト**
- React: useTaskStream → SSE接続 → TaskMonitor表示
- Streamlit: JobStore → 同一機能比較

### グループH: AnalyticsTab機能（ステップ43-48）

**ステップ43: React AnalyticsTabを確認**
ファイル: `frontend/src/components/tabs/AnalyticsTab.tsx`

**ステップ44: Streamlit分析機能を検索**
```bash
grep -r "analytics\|optimization\|metric" streamlit_app/ --include="*.py" -l
```
主なファイル: ui_tabs_analytics.py, api_client.py

**ステップ45: React API分析操作を確認**
```typescript
// frontend/src/api.ts
getOptHistory(), critiqueOptimize(), getPendingPatches(),
getPromptVersions(), getNarrativeMetricsTrend()
```

**ステップ46: Streamlit ui_tabs_analytics.pyを確認**
```python
# 分析・最適化・パッチ管理機能
```

**ステップ47: useUIStore(optHistory等)を確認**
```typescript
// frontend/src/store/useUIStore.ts
// optHistory, pendingPatches, promptVersions等
```

**ステップ48: Analytics機能整合性テスト**
- React: AnalyticsTab → 各API → 分析ダッシュボード
- Streamlit: 同一機能比較

---

## Phase 2: Streamlit機能React移植（ステップ49-60）

### グループI: Streamlit→React移植（ステップ49-54）

**ステップ49: PlanningTab React実装確認**
ファイル: `frontend/src/components/tabs/PlanningTab.tsx`
現状: 存在確認済み

**ステップ50: AuditTab React実装確認**
ファイル: `frontend/src/components/tabs/AuditTab.tsx`
現状: 存在確認済み

**ステップ51: StyleLabTab/ImportTab確認**
ファイル: `frontend/src/components/tabs/StyleLabTab.tsx`, `ImportTab.tsx`

**ステップ52: 不足TabsのStreamlit実装を調査**
```bash
# AuditTab対応Streamlit
cat streamlit_app/ui_tabs_audit.py

# StyleLab対応Streamlit
grep -r "style" streamlit_app/ --include="*.py"
```

**ステップ53: ReactTabs不足分を実装**
各Tabの実装状況に応じて:
- PlanningTab: handlePlanGeneration実装
- AuditTab: selectedBook連携確認
- ImportTab: ImportChapterDialog連携確認

**ステップ54: 全ReactTabs統合テスト**
```bash
cd frontend && npm run build
# 全Tab正常動作確認
```

### グループJ: API Client統合（ステップ55-60）

**ステップ55: Streamlit api_client.py全関数をリスト化**
```python
# streamlit_app/api_client.py
# 主要関数:
# - generate_easy, generate_episodes, expand_plots, rebuild_plots
# - critique_optimize, plan_generation, retry_failed_episodes
# - get_task_status, stop_task
# - list_books, get_book, delete_book
# - get_plots, get_chapters, create_chapter, delete_chapter
# - get_bible, get_opt_history
# - analyze_style_dna, export_package, generate_marketing
# - audit_producer_plan, get_issues, resolve_issue, import_chapter
```

**ステップ56: React api.ts全関数をリスト化**
```typescript
// frontend/src/api.ts
// 主要関数:
# 同期済み: getBooks, getBook, deleteBook, getPlots, getChapters, getBible
# 同期済み: getTaskStatus, stopTask, connectTaskStream
# 同期済み: generateEasy, planGeneration, generateEpisodes, expandPlots, rebuildPlots
# 同期済み: critiqueOptimize, auditPlan, importChapter, generateMarketing
# 同期済み: getPendingPatches, approvePatch, rejectPatch, editPatch
# 同期済み: getPromptVersions, rollbackPromptVersion, getNarrativeMetricsTrend
```

**ステップ57: 不足API関数をReact api.tsに追加**
差分を確認し、必要に応じて追加:
```typescript
// 例: 不足していたら追加
export async function getIssues(bookId: number): Promise<Issue[]> {
  return apiRequest(`${API_BASE_URL}/issues/books/${bookId}`);
}
```

**ステップ58: React API Clientテスト作成**
```typescript
// frontend/src/test/api.test.ts
// 主要API関数のモックテスト
```

**ステップ59: CORS設定確認**
```python
# src/backend/server.py
# allow_origins設定を確認（環境変数対応済みか）
```

**ステップ60: API Client統合テスト実行**
```bash
cd frontend && npm run build
cd autonovel && python -m pytest tests/integration/ -v
```

---

## Phase 3: Streamlit段階的無効化（ステップ61-66）

### グループK: Streamlit機能無効化Step1（ステップ61-63）

**ステップ61: Streamlitページング設定を修正**
```python
# streamlit_app/pages_config.py
# React実装済み機能のページを非表示化
```

**ステップ62: Streamlit navigationを修正**
```python
# streamlit_app/app.py - _run_navigation関数
# Reactへ移行済みの機能をスキップ
```

**ステップ63: Streamlit UI tabsをReactへリダイレクト**
```python
# streamlit_app/ui_tabs_*.py
# 代わりにReactURLへリダイレクトするメッセージを表示
```

### グループL: Streamlit機能無効化Step2（ステップ64-66）

**ステップ64: Streamlit Landing pageを修正**
```python
# streamlit_app/landing.py
# Reactアプリへアクセスするよう誘導
```

**ステップ65: Streamlit Sidebarを修正**
```python
# streamlit_app/sidebar.py
# ReactへのナビゲーションLinksに修正
```

**ステップ66: Streamlit Health checkを修正**
```python
# streamlit_app/health_check.py
# ReactのHealthGateと統合
```

---

## Phase 4: Streamlit削除準備（ステップ67-70）

### グループM: Streamlit削除準備（ステップ67-70）

**ステップ67: Streamlit依存ファイル一覧を作成**
```bash
# streamlit_app/ 内の全Pythonファイル
# 削除対象: *.py ファイル
# 保持対象: なし（完全削除）
```

**ステップ68: バックエンドStreamlit関連設定を削除**
```bash
# docker-compose.yml
# streamlit相關service設定 제거
```

**ステップ69: ドキュメント更新**
```markdown
# docs/README.md
# React足を-main UIに変更
# Streamlit相關記述を削除
```

**ステップ70: 削除前最終バックアップ**
```bash
cd autonovel
mkdir -p backup/pre_delete_backup
cp -r streamlit_app backup/pre_delete_backup/
cp -r frontend/src backup/pre_delete_backup/
```

---

## Phase 5: 完全移行完了（ステップ71-72）

### グループN: 最終確認と削除（ステップ71-72）

**ステップ71: Streamlitアプリ起動テスト**
```bash
cd frontend && npm run dev
# ブラウザで全機能確認
```

**ステップ72: Streamlitディレクトリ削除と最終確認**
```bash
# 最終確認後、削除を実行
rm -rf streamlit_app/
cd frontend && npm run build
# 本番イメージをビルドして完了
```

---

## 72ステップ総括表

| Phase | ステップ | 主要タスク |
|-------|---------|-----------|
| Phase 0 | 1-12 | 分析・バックアップ・基盤確認 |
| Phase 1 | 13-48 | React機能確認・整合性テスト |
| Phase 2 | 49-60 | Streamlit→React移植・API統合 |
| Phase 3 | 61-66 | Streamlit段階的無効化 |
| Phase 4 | 67-70 | Streamlit削除準備 |
| Phase 5 | 71-72 | 完全移行完了 |

---

## ADR-0003対応表

| ADRフェーズ | 本計画対応 |
|------------|-----------|
| Phase 0 | ステップ1-12 |
| Phase 1 | ステップ13-48 |
| Phase 2 | ステップ49-60 |
| Phase 3 | ステップ61-66 |
| Phase 4 | ステップ67-72 |

---

## 注意事項

1. **ステップ1-6を必ず最初に実行**: バックアップなしでは開始しない
2. **各ステップ完了後にテスト**: 問題を早期発見
3. **ステップ71で完全動作確認**: Streamlit削除前に全機能検証
4. **低性能LLM向け**: 各ステップは小さく、1回の操作で完了する規模