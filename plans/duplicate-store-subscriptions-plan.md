# 重複ストア購読最適化実装計画

## 問題分析

現在のコードでは、複数のコンポーネントがstoreを購読する際に **selectorを使用せず** に直接オブジェクト全体を取得している。

```typescript
// 問題: store全体订阅 → どのstate変更でも再レンダリング
const { activeTab } = useProjectStore();

// 改善: selector使用 → 特定state変更時のみ再レンダリング
const activeTab = useProjectStore((s) => s.activeTab);
```

**問題ファイル:**
- `useAppActions.ts` - 6つのstoreを非効率に購読
- `useBookDetails.ts` - 2つのstoreを非効率に購読
- `useTaskMonitor.ts` - useTaskStoreを非効率に購読
- 複数タブコンポーネントでも同様

---

## ステップ1-8: セLECTORユーティリティ作成

### ステップ1: store/selectors/ディレクトリ作成
```
src/store/selectors/
  ├── projectSelectors.ts
  ├── uiSelectors.ts
  ├── bookSelectors.ts
  ├── writingSelectors.ts
  ├── taskSelectors.ts
  ├── userSettingsSelectors.ts
  └── easyModeSelectors.ts
```

### ステップ2: projectSelectors.ts 作成
```typescript
import { useProjectStore } from '../useProjectStore';

export const selectActiveTab = (s) => s.activeTab;
export const selectSelectedBookId = (s) => s.selectedBookId;
export const selectProjectActions = (s) => ({
  setActiveTab: s.setActiveTab,
  setSelectedBookId: s.setSelectedBookId,
});
```

### ステップ3: uiSelectors.ts 作成
```typescript
import { useUIStore } from '../useUIStore';

export const selectIsCreateModalOpen = (s) => s.isCreateModalOpen;
export const selectGlobalError = (s) => s.globalError;
export const selectOptHistory = (s) => s.optHistory;
export const selectPendingPatches = (s) => s.pendingPatches;
export const selectPromptVersions = (s) => s.promptVersions;
export const selectMetricTrend = (s) => s.metricTrend;
export const selectUIActions = (s) => ({
  setCreateModalOpen: s.setCreateModalOpen,
  setGlobalError: s.setGlobalError,
  setOptHistory: s.setOptHistory,
  setPendingPatches: s.setPendingPatches,
  setPromptVersions: s.setPromptVersions,
  setMetricTrend: s.setMetricTrend,
});
```

### ステップ4: bookSelectors.ts 作成
```typescript
import { useBookStore } from '../useBookStore';

export const selectSelectedBook = (s) => s.selectedBook;
export const selectChapters = (s) => s.chapters;
export const selectPlots = (s) => s.plots;
export const selectBible = (s) => s.bible;
export const selectBookActions = (s) => ({
  setSelectedBook: s.setSelectedBook,
  setChapters: s.setChapters,
  setPlots: s.setPlots,
  setBible: s.setBible,
  clearBookData: s.clearBookData,
});
```

### ステップ5: writingSelectors.ts 作成
```typescript
import { useWritingStore } from '../useWritingStore';

export const selectWriteFrom = (s) => s.writeFrom;
export const selectWriteTo = (s) => s.writeTo;
export const selectWritePassion = (s) => s.writePassion;
export const selectImportEpNum = (s) => s.importEpNum;
export const selectImportText = (s) => s.importText;
export const selectImportDoRefine = (s) => s.importDoRefine;
export const selectGenre = (s) => s.genre;
export const selectTitle = (s) => s.title;
export const selectWordCount = (s) => s.wordCount;
export const selectPlatform = (s) => s.platform;
export const selectShowPreview = (s) => s.showPreview;
export const selectWritingError = (s) => s.error;
export const selectWritingActions = (s) => ({
  setWriteFrom: s.setWriteFrom,
  setWriteTo: s.setWriteTo,
  setWritePassion: s.setWritePassion,
  setImportEpNum: s.setImportEpNum,
  setImportText: s.setImportText,
  setImportDoRefine: s.setImportDoRefine,
  setGenre: s.setGenre,
  setTitle: s.setTitle,
  setWordCount: s.setWordCount,
  setPlatform: s.setPlatform,
  setShowPreview: s.setShowPreview,
  setError: s.setError,
  clearError: s.clearError,
  resetImport: s.resetImport,
});
```

### ステップ6: taskSelectors.ts 作成
```typescript
import { useTaskStore } from '../useTaskStore';

export const selectActiveTaskId = (s) => s.activeTaskId;
export const selectTaskStatus = (s) => s.taskStatus;
export const selectTaskActions = (s) => ({
  setActiveTaskId: s.setActiveTaskId,
  setTaskStatus: s.setTaskStatus,
  clearTask: s.clearTask,
});
```

### ステップ7: userSettingsSelectors.ts 作成
```typescript
import { useUserSettingsStore } from '../useUserSettingsStore';

export const selectApiKey = (s) => s.apiKey;
export const selectTemperature = (s) => s.temperature;
export const selectModelType = (s) => s.modelType;
export const selectIsExpertMode = (s) => s.isExpertMode;
export const selectUserSettingsActions = (s) => ({
  setApiKey: s.setApiKey,
  setTemperature: s.setTemperature,
  setModelType: s.setModelType,
  setIsExpertMode: s.setIsExpertMode,
});
```

### ステップ8: easyModeSelectors.ts 作成
```typescript
import { useEasyModeStore } from '../useEasyModeStore';

export const selectEasyGenre = (s) => s.easyGenre;
export const selectEasyKeywords = (s) => s.easyKeywords;
export const selectEasyArchetype = (s) => s.easyArchetype;
export const selectEasyStyleKey = (s) => s.easyStyleKey;
export const selectEasyTargetEps = (s) => s.easyTargetEps;
export const selectEasyWordCount = (s) => s.easyWordCount;
export const selectEasyConcept = (s) => s.easyConcept;
export const selectEnableErotic = (s) => s.enableErotic;
export const selectEroticIntensity = (s) => s.eroticIntensity;
export const selectEnableIllustration = (s) => s.enableIllustration;
export const selectIllustrationType = (s) => s.illustrationType;
export const selectIllustrationModel = (s) => s.illustrationModel;
export const selectGenerateCover = (s) => s.generateCover;
export const selectGenerateEpisodeIllustrations = (s) => s.generateEpisodeIllustrations;
export const selectEpisodeInterval = (s) => s.episodeInterval;
export const selectEasyModeActions = (s) => ({
  setEasyGenre: s.setEasyGenre,
  setEasyKeywords: s.setEasyKeywords,
  setEasyArchetype: s.setEasyArchetype,
  setEasyStyleKey: s.setEasyStyleKey,
  setEasyTargetEps: s.setEasyTargetEps,
  setEasyWordCount: s.setEasyWordCount,
  setEasyConcept: s.setEasyConcept,
  setEnableErotic: s.setEnableErotic,
  setEroticIntensity: s.setEroticIntensity,
  setEnableIllustration: s.setEnableIllustration,
  setIllustrationType: s.setIllustrationType,
  setIllustrationModel: s.setIllustrationModel,
  setGenerateCover: s.setGenerateCover,
  setGenerateEpisodeIllustrations: s.setGenerateEpisodeIllustrations,
  setEpisodeInterval: s.setEpisodeInterval,
});
```

---

## ステップ9-16: hooks の最適化

### ステップ9: useAppActions.ts 最適化（前半）
```typescript
// 変更前
const { apiKey, temperature, modelType } = useUserSettingsStore();

// 変更後
const apiKey = useUserSettingsStore((s) => s.apiKey);
const temperature = useUserSettingsStore((s) => s.temperature);
const modelType = useUserSettingsStore((s) => s.modelType);
```

### ステップ10: useAppActions.ts 最適化（中盤1）
```typescript
// 変更前
const { activeTab } = useProjectStore();
const { selectedBook } = useBookStore();

// 変更後
const activeTab = useProjectStore((s) => s.activeTab);
const selectedBook = useBookStore((s) => s.selectedBook);
```

### ステップ11: useAppActions.ts 最適化（中盤2）
```typescript
// 変更前
const { setCreateModalOpen, setGlobalError } = useUIStore();

// 変更後
const setCreateModalOpen = useUIStore((s) => s.setCreateModalOpen);
const setGlobalError = useUIStore((s) => s.setGlobalError);
```

### ステップ12: useAppActions.ts 最適化（後半1）
```typescript
// 変更前
const { easyWordCount } = useEasyModeStore();

// 変更後
const easyWordCount = useEasyModeStore((s) => s.easyWordCount);
```

### ステップ13: useAppActions.ts 最適化（後半2）
```typescript
// 変更前
const {
  writeFrom, writeTo, writePassion, importEpNum,
  importText, importDoRefine, resetImport, wordCount,
} = useWritingStore();

// 変更後
const writeFrom = useWritingStore((s) => s.writeFrom);
const writeTo = useWritingStore((s) => s.writeTo);
const writePassion = useWritingStore((s) => s.writePassion);
const importEpNum = useWritingStore((s) => s.importEpNum);
const importText = useWritingStore((s) => s.importText);
const importDoRefine = useWritingStore((s) => s.importDoRefine);
const resetImport = useWritingStore((s) => s.resetImport);
const wordCount = useWritingStore((s) => s.wordCount);
```

### ステップ14: useAppActions.ts 最適化（後半3）
```typescript
// 変更前
const { setError: setWritingError } = useWritingStore();

// 変更後
const setWritingError = useWritingStore((s) => s.setError);
```

### ステップ15: useAppActions.ts 最適化（後半4）
```typescript
// 変更前
const { setActiveTaskId, activeTaskId, setTaskStatus } = useTaskStore();

// 変更後
const setActiveTaskId = useTaskStore((s) => s.setActiveTaskId);
const activeTaskId = useTaskStore((s) => s.activeTaskId);
const setTaskStatus = useTaskStore((s) => s.setTaskStatus);
```

### ステップ16: useAppActions.ts の依存配列更新
```typescript
// useCallback の依存配列を個別のselectorに変更
const loadBookDetails = useBookDetails(selectedBook?.id ?? null, activeTab);
// ※ activeTab は変更されないのでOK
```

---

## ステップ17-20: components の最適化

### ステップ17: useTaskMonitor.ts 最適化
```typescript
// 変更前
const { activeTaskId, taskStatus, setActiveTaskId, setTaskStatus } = useTaskStore();

// 変更後
const activeTaskId = useTaskStore((s) => s.activeTaskId);
const taskStatus = useTaskStore((s) => s.taskStatus);
const setActiveTaskId = useTaskStore((s) => s.setActiveTaskId);
const setTaskStatus = useTaskStore((s) => s.setTaskStatus);
```

### ステップ18: TaskMonitor.tsx 最適化
```typescript
// 変更前
const { activeTaskId, taskStatus } = useTaskStore();

// 変更後
const activeTaskId = useTaskStore((s) => s.activeTaskId);
const taskStatus = useTaskStore((s) => s.taskStatus);
```

### ステップ19: WriteTab.tsx 最適化
```typescript
// 変更前
const { error, clearError } = useWritingStore();

// 変更後
const error = useWritingStore((s) => s.error);
const clearError = useWritingStore((s) => s.clearError);
```

### ステップ20: StyleLabTab.tsx, PlanningTab.tsx, Sidebar.tsx 最適化
```typescript
// StyleLabTab.tsx - 変更前
const apiKey = useUserSettingsStore((s) => s.apiKey);
// ※ すでに正しいパターン

// PlanningTab.tsx - 変更前
const { wordCount, setWordCount } = useWritingStore();
// 変更後
const wordCount = useWritingStore((s) => s.wordCount);
const setWordCount = useWritingStore((s) => s.setWordCount);

// Sidebar.tsx - 変更前
const { apiKey, setApiKey, modelType, setModelType, isExpertMode, setIsExpertMode } = useUserSettingsStore();
// 変更後
const apiKey = useUserSettingsStore((s) => s.apiKey);
const setApiKey = useUserSettingsStore((s) => s.setApiKey);
const modelType = useUserSettingsStore((s) => s.modelType);
const setModelType = useUserSettingsStore((s) => s.setModelType);
const isExpertMode = useUserSettingsStore((s) => s.isExpertMode);
const setIsExpertMode = useUserSettingsStore((s) => s.setIsExpertMode);
```

---

## ステップ21-22: AppContext.tsx 確認（既存は正しい）

### ステップ21: AppContext.tsx 監査
```typescript
// 既にselectorパターンで実装済みなので変更不要
const activeTab = useProjectStore((s) => s.activeTab);
const selectedBook = useBookStore((s) => s.selectedBook);
```

---

## ステップ23: テスト実行

### ステップ23: ビルド＆lint確認
```bash
cd autonovel/frontend
npm run build
npm run lint
```

---

## ステップ24: 検証

### ステップ24: 動作確認項目
- [ ] ページ遷移時にactiveTabが正しく変わる
- [ ]  модель選択時にmodelTypeが正しく変わる
- [ ] 執筆タスク起動時にactiveTaskIdが正しく変わる
- [ ] useAppActions 各handlerが正常に動作
- [ ] Browser DevToolsで不必要的再レンダリングなし

---

## 期待効果

| 指標 | 改善前 | 改善後 |
|------|--------|--------|
| 再レンダリング数 | 各state変更で全store購読者 | 該当state購读者的のみ |
| メモリ使用 | 購読オブジェクト保持多数 | 最小化 |
| コード保守性 | 散在するstore参照 | selectors/集中管理 |

---

## 補足: Zustand shallow比較（オブジェクト返すselector用）

複数フィールドを返すselector使用時:
```typescript
import { shallow } from 'zustand/shallow';

// OK: そのままでは古い参照 проблема
const { setActiveTab, setSelectedBookId } = useProjectStore(
  (s) => ({ setActiveTab: s.setActiveTab, setSelectedBookId: s.setSelectedBookId })
);

// 改善: shallow比較使用
const { setActiveTab, setSelectedBookId } = useProjectStore(
  (s) => ({ setActiveTab: s.setActiveTab, setSelectedBookId: s.setSelectedBookId }),
  shallow
);
```