# App.tsx 分解・再構成 自走計画書

## 現状分析

| 指標 | 現値 | 目標値 |
|------|------|--------|
| 行数 | 310行 | ~100行 |
| インポート数 | 15+ | ~5 |
| ストア購読 | 8 | ~2（コンテキスト統合後） |
| アクションハンドラ | 7 | 0（hooksに移動） |
| useEffect | 4 | 0（hooksに移動） |

---

## 12ステップ リファクタリング計画

### Phase 1: 基盤整理（Step 1-3）

---

#### Step 1: AppContext の作成（ストア購読の統合）

**目的**: 8つのストア購読を1つのコンテキストに統合

**対象ファイル作成**: `src/contexts/AppContext.tsx`

**作業内容**:
```
1. createContext を作成し、全ストアを購読する Provider を実装
2. コンテキスト値として以下を提供:
   - userSettings: { apiKey, setIsExpertMode }
   - project: { activeTab, setActiveTab }
   - book: { selectedBook, setSelectedBook, chapters, bible, plots }
   - ui: { isCreateModalOpen, setCreateModalOpen, globalError, setGlobalError, ... }
   - task: { activeTaskId, setActiveTaskId, taskStatus, setTaskStatus }
   - writing: { writeFrom, setWriteFrom, writeTo, setWriteTo, ... }
3. useAppContext() hooks をexport
```

**受益**:
- コンポーネント木のprops drilling削減
- テスト時のmock容易化
- ストア追加時の影響範囲限定

---

#### Step 2: AppActions Hook の独立化

**目的**: 7つのアクションハンドラを App.tsx から分離

**対象ファイル**: `src/hooks/useAppActions.ts`（既存）

**検証ポイント**:
```typescript
// 移動対象ハンドラ
handleCreateEasyMode      → useAppActions
handleTriggerWriting      → useAppActions
handleExpandPlots         → useAppActions
handleCritiqueOptimize     → useAppActions
handleImportChapter       → useAppActions
handleGenerateMarketing   → useAppActions
handleRefineErotic        → useAppActions
```

**作業内容**:
```
1. useAppActions hook を App.tsx から独立ファイルへ
2. 内部で AppContext を使用
3. 型定義を useAppActions.types.ts として分離
```

---

#### Step 3: useTaskStream + useTaskMonitor 統合 Hook 化

**目的**: Task関連ロジックをApp.tsxから分離

**対象ファイル作成**: `src/hooks/useTaskStreamSetup.ts`

**作業内容**:
```
1. useTaskStream, handleTaskStatus, handleTaskComplete, handleTaskError を統合
2. useTaskStreamSetup(selectedBook, loadBookDetails) hook として抽象化
3. App.tsx では単一useTaskStreamSetup()呼び出しに
```

---

### Phase 2: UIコンポーネント分割（Step 4-6）

---

#### Step 4: Header セクションのコンポーネント化

**目的**: APIステータスバーとタイトル表示を分離

**対象ファイル作成**: `src/components/AppHeader.tsx`

**作業内容**:
```
1. AppHeader コンポーネント抽出
2. activeTab に応じたタイトル表示をprops或いはcontextから取得
3. globalError 状態によるAPI Status 表示
```

**Before/After**:
```tsx
// Before (App.tsx 内)
<header style={{ display: 'flex', justifyContent: 'space-between', ... }}>
  <div>
    <h1 style={{ fontSize: '2rem', ... }}>
      {activeTab === 'landing' && '🚀 ホーム・ダッシュボード'}
      ...
    </h1>
  </div>
  <div>...API Status...</div>
</header>

// After
<AppHeader />
```

---

#### Step 5: TabContainer によるタブ管理

**目的**: タブ切り替えロジックを専用コンポーネントに

**対象ファイル作成**: `src/components/tab-navigation/TabContainer.tsx`

**作業内容**:
```
1. TabContainer コンポーネント作成
2. activeTab に応じた子コンポーネント切り替え
3. 各タブコンポーネントへのprops渡をここで完結
```

**分割後のApp.tsxイメージ**:
```tsx
<TabContainer
  activeTab={activeTab}
  selectedBook={selectedBook}
  onTabChange={setActiveTab}
  handlers={appActions} // ハンドラ群を纏めて渡
/>
```

---

#### Step 6: 各Tabコンポーネントへの進一步分割

**目的**: 各タブの中身を小さなコンポーネント群へ

**作業割当**:

| タブ | 担当ファイル |
|------|-------------|
| Landing | LandingTab → LandingHeader + QuickActions |
| Books | BooksTab → BookList + BookCard + CreateModalTrigger |
| Plots | PlotsTab → PlotTimeline + PlotNode |
| Write | WriteTab → ChapterList + WriteForm + StreamingLog |
| Analytics | AnalyticsTab → MetricChart + PatchPanel |
| Planning | PlanningTab → PlanGenerator |
| StyleLab | StyleLabTab（単一維持可） |
| Audit | AuditTab（単一維持可） |

---

### Phase 3: Sidebar + 浮动UI分離（Step 7-9）

---

#### Step 7: Sidebar のAppからの独立

**目的**: SidebarをAppの子供ではなく兄弟コンポーネントに

**対象ファイル変更**: `src/App.tsx`, ルーティング層

**作業内容**:
```
1. App.tsx から <Sidebar /> 移除
2. 親コンポーネント（Router/MainLayout）で Sidebar + App を並列配置
3. AppContext で activeTab 管理を継続
```

---

#### Step 8: TaskMonitor / EasyModeDialog のAppから分離

**目的**: 浮动UIをAppの責任から除外

**対象ファイル変更**: `src/App.tsx`

**作業内容**:
```
1. TaskMonitor → グローバルoverlay管理層へ移動
2. EasyModeDialog → BookContext 内で管理
3. App.tsx では TaskMonitor, EasyModeDialog のrender担当のみ
```

---

#### Step 9: App.tsx 本体の骨的設計

**目的**: App.tsxを純粋なレイアウトコンテナに

**リザルト目標**:
```tsx
export default function App() {
  return (
    <HealthGate>
      <AppContext.Provider>
        <div className="flex w-full min-h-screen bg-[var(--bg-main)]">
          <Sidebar />
          <main>
            <AppHeader />
            <TabContainer />
          </main>
          <FloatingOverlay />
        </div>
      </AppContext.Provider>
    </HealthGate>
  );
}
```

---

### Phase 4: 仕上げ（Step 10-12）

---

#### Step 10: useBooks + useBookDetails の統合または整理

**目的**: Book関連hooksの重複解決

**作業内容**:
```
1. useBooks + useBookDetails の相依関係分析
2. 可能なら単一 useBook(selectedBookId) hook へ統合
3. そうでなければ責務明確化:
   - useBooks: 作品一覧取得/削除
   - useBookDetails: 選択中作品のDetail取得
```

---

#### Step 11: 型定義・index文件的整理

**目的**: エントリーポイント明確化と循環参照防止

**作業内容**:
```
1. src/components/tabs/index.ts で各Tabをexport
2. src/contexts/index.ts でContext関連をexport
3. src/hooks/index.ts で全カスタムhooksをexport
4. App.tsx のimport文整理
```

---

#### Step 12: テスト環境構築と最終確認

**目的**: リファクタリング後の品質担保

**テスト対象**:
```
1. App.test.tsx: 最低限のrender test
2. TabContainer.test.tsx: 各タブへのswitching test
3. AppContext.test.tsx: Provider + 購読test
4. 各Hookのunit test
```

**検証項目**:
- [ ] App.tsx 行数: 310 → ~80
- [ ] import数: 15+ → ~8
- [ ] ストア直接購読: 8 → 0 (Context経由)
- [ ] useEffect: 4 → 0
- [ ] local state: 1 → 0

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| Context爆増 | ContextはAppContext1つに統合し小さく保つ |
| Props Drilling | Context + hooksで补给、深いprops不要に |
| テスト不能 | 各Unitが小さく单一責務でているのでindividual test可能 |
| 循環参照 | index.ts 통한明示的exportで防止 |

---

## 完了条件

1. App.tsxが80行以下
2. 直接インポートするストアが0
3. 全アクションハンドラがhooksにある
4. 全てのTabが独立コンポーネント
5. 既存の機能テストが全て通過