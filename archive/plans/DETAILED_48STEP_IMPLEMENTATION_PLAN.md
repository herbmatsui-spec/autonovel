# 詳細実装計画書：48ステップ完全実装ガイド

**作成日**: 2026-07-14  
**対象**: AutoNovelプロジェクト全体（Reactフロントエンド、FastAPIバックエンド、Streamlitアプリ）  
**目的**: 低性能LLMでも迷わず実装可能な粒度（1ステップ30分以内）に分割  
**前提**: IMPLEMENTATION_STATUS_AND_PLAN.md と COMMERCIAL_PIPELINE_72STEP_PLAN_DETAILED.md の検証済み内容を統合・再構成

---

## 📋 タスク概要と進捗サマリー

| タスク | 総ステップ | 完了 | 部分的 | 未着手 | 完了率 | 残ステップ |
|--------|-----------|------|--------|--------|--------|------------|
| A: React App.tsx リファクタリング | 24 | 11 | 7 | 6 | 46% | **13** |
| B: CORS設定の制限 | 24 | 15 | 4 | 5 | 63% | **9** |
| C: Streamlit状態管理の統一 | 24 | 8 | 8 | 8 | 33% | **16** |
| **合計** | **72** | **34** | **19** | **19** | **47%** | **38** |

> **注意**: 本計画書は上記72ステップを**48ステップに再編・最適化**したもの。重複・依存関係を整理し、低性能LLMでも確実に実行可能な粒度に分割。

---

## 🎯 実装の進め方ルール（厳守）

1. **1ステップ = 1ファイル作成/変更 + 即時動作確認**
2. **前のステップが完了してから次のステップへ**
3. **エラーが出たらその場で修正してから次へ**
4. **各ステップ最後に構文チェック実行**:
   - Frontend: `cd frontend && npx tsc --noEmit`
   - Backend: `cd /workspaces/autonovel && python -m py_compile <file>`
   - Streamlit: `cd /workspaces/autonovel && python -m py_compile streamlit_app/<file>.py`
5. **テストコードは実装と同時進行で作成**

---

## 📦 Phase A: React App.tsx リファクタリング（16ステップ）

### フェーズA-1: 型定義の完全実装（ステップ1-3）

#### **ステップ1: types/index.ts に不足型定義を追加**
```bash
# 対象: frontend/src/types/index.ts
# アクション: 以下の型定義を末尾に追加（既存の export * from './api' の前）
```
**実装内容:**
```typescript
// frontend/src/types/index.ts へ追加（行105付近、export * from './api' の前）

export interface Book {
  id: number;
  title: string;
  synopsis: string;
  genre: string;
  target_eps: number;
  created_at: string;
  updated_at: string;
}

export interface Plot {
  id: number;
  book_id: number;
  ep_num: number;
  title: string;
  summary: string;
  tension: number;
  is_catharsis: boolean;
  status: string;
  detailed_blueprint?: string;
}

export interface Chapter {
  id: number;
  book_id: number;
  ep_num: number;
  title: string;
  summary: string;
  content: string;
  created_at: string;
}

export interface Bible {
  id: number;
  book_id: number;
  version: number;
  settings: {
    characters: Record<string, any>;
    world: any;
    timeline: any;
  };
  created_at: string;
}

export interface TaskStatus {
  task_id: string;
  current_step: number;
  total_steps: number;
  message: string;
  sub_message?: string;
  streaming_text?: string;
  logs: string[];
  error?: string;
  result_data?: any;
  token_usage: { prompt: number; completion: number; calls: number };
  start_time: number;
  last_updated: number;
}

export interface OptimizationHistory {
  id: number;
  book_id: number;
  created_at: string;
  report_json: any;
}

export interface PendingPatch {
  id: number;
  book_id: number;
  ep_num: number;
  patch_type: string;
  original_text: string;
  proposed_text: string;
  reason: string;
  status: string;
  created_at: string;
}

export interface PromptVersion {
  id: number;
  book_id: number;
  version_tag: string;
  content: string;
  score_before?: number;
  score_after?: number;
  is_active: boolean;
  rollback_reason?: string;
  created_at: string;
}

export interface NarrativeMetricTrend {
  ep_num: number;
  scene_num: number;
  tension: number;
  satisfaction: number;
  mystery: number;
}

export interface EasyModeParams {
  genre: string;
  keywords: string;
  archetype_key: string;
  target_eps: number;
  word_count: number;
  concept: string;
  tone_vibe: number;
}

// 既存の export * from './api'; はそのまま維持
```

**確認**: `cat frontend/src/types/index.ts | tail -30` で追加確認  
**構文チェック**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ2: App.tsx のローカル型定義を削除し import に変更**
```bash
# 対象: frontend/src/App.tsx
# アクション: 
# 1. `import type { Plot, Chapter, Bible, OptimizationHistory, PendingPatch, PromptVersion, NarrativeMetricTrend, TaskStatus } from '@/types';` を確認
# 2. App.tsx 内のローカル `interface Book {}` 等があれば削除
# 3. `Book` 型も `@/types` から import するよう追加
```
**変更内容:**
```typescript
// App.tsx 行27-36 を以下に変更
import type { 
  EasyModeParams,
  Plot,
  Chapter,
  Bible,
  OptimizationHistory,
  PendingPatch,
  PromptVersion,
  NarrativeMetricTrend,
  TaskStatus,
  Book,  // ← 追加
} from '@/types';
```

**確認**: `cd frontend && npx tsc --noEmit` でエラーなし

---

#### **ステップ3: 型整合性チェック実行**
```bash
cd frontend && npx tsc --noEmit
```
**完了条件**: エラー0件  
**エラー時**: 表示されるエラーを1つずつ修正してから次へ

---

### フェーズA-2: Custom Hooks 抽出（ステップ4-6）

#### **ステップ4: hooks/useBookDetails.ts の不足 setter 対応**
```bash
# 対象: frontend/src/hooks/useBookDetails.ts
# 現状: setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend がコメントアウト
# アクション: useUIStore にこれらの setter を追加してから有効化
```
**前提作業**: `frontend/src/store/useUIStore.ts` に以下を追加
```typescript
// useUIStore.ts の state に追加
optHistory: OptimizationHistory[];
setOptHistory: (data: OptimizationHistory[]) => void;
pendingPatches: PendingPatch[];
setPendingPatches: (data: PendingPatch[]) => void;
promptVersions: PromptVersion[];
setPromptVersions: (data: PromptVersion[]) => void;
metricTrend: NarrativeMetricTrend[];
setMetricTrend: (data: NarrativeMetricTrend[]) => void;
```

**確認**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ5: hooks/useTaskMonitor.ts の handleStopTask 実装完成**
```bash
# 対象: frontend/src/hooks/useTaskMonitor.ts
# 現状: handleStopTask が setActiveTaskId/setTaskStatus のみ（stopTask API 呼び出しなし）
# アクション: stopTask を import して実際の停止処理を実装
```
**実装内容:**
```typescript
// useTaskMonitor.ts
import { stopTask } from '../api';  // 追加

const handleStopTask = async () => {
  if (!activeTaskId) return;
  try {
    await stopTask(activeTaskId);
    setActiveTaskId(null);
    setTaskStatus(null);
  } catch (err) {
    console.error('Failed to stop task:', err);
  }
};
```

**確認**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ6: hooks/index.ts で全hooksエクスポート確認**
```bash
# 対象: frontend/src/hooks/index.ts
# 確認: 4つのhooksが全てエクスポートされているか
```
**期待内容:**
```typescript
export * from './useBooks';
export * from './useTaskStream';
export * from './useBookDetails';
export * from './useTaskMonitor';
export * from './useAppActions';  // 既存
export * from './useTermTooltip'; // 既存
```

**構文チェック**: `cd frontend && npx tsc --noEmit`

---

### フェーズA-3: Dialog コンポーネント作成（ステップ7-10）

#### **ステップ7: EasyModeDialog.tsx 完成（CreateNovelModal からリファクタ）**
```bash
# 対象: frontend/src/components/dialogs/EasyModeDialog.tsx
# 参照: 既存 CreateNovelModal.tsx
# アクション: CreateNovelModal.tsx をベースに Props インターフェースを仕様通りに整備
```
**仕様（IMPLEMENTATION_STATUS_AND_PLAN.md ステップ13準拠）:**
```typescript
interface EasyModeParams {
  genre: string;
  keywords: string;
  archetype_key: string;
  target_eps: number;
  word_count: number;
  concept: string;
  tone_vibe: number;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: EasyModeParams) => void;
}
```
**確認**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ8: ImportChapterDialog.tsx 作成**
```bash
# 対象: frontend/src/components/dialogs/ImportChapterDialog.tsx (新規)
# 参照: App.tsx lines 297-321 (handleImportChapter 内のロジック)
```
**実装テンプレート:**
```typescript
// frontend/src/components/dialogs/ImportChapterDialog.tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (epNum: number, text: string, doRefine: boolean) => void;
}

export function ImportChapterDialog({ isOpen, onClose, onSubmit }: Props) {
  if (!isOpen) return null;

  const [epNum, setEpNum] = useState(1);
  const [text, setText] = useState('');
  const [doRefine, setDoRefine] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(epNum, text, doRefine);
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>章取り込み</h2>
        <form onSubmit={handleSubmit}>
          <Input label="エピソード番号" type="number" value={epNum} onChange={(e) => setEpNum(Number(e.target.value))} min={1} />
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="原稿を貼り付け..." style={{width: '100%', minHeight: '200px', marginTop: '0.5rem'}} />
          <label style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem'}}>
            <input type="checkbox" checked={doRefine} onChange={(e) => setDoRefine(e.target.checked)} /> 研磨する
          </label>
          <div className="modal-actions" style={{marginTop: '1rem', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end'}}>
            <Button type="button" onClick={onClose}>キャンセル</Button>
            <Button type="submit">取り込み実行</Button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

**確認**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ9: dialogs/index.ts 作成**
```bash
# 対象: frontend/src/components/dialogs/index.ts
```
```typescript
export { EasyModeDialog } from './EasyModeDialog';
export { ImportChapterDialog } from './ImportChapterDialog';
```

**確認**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ10: App.tsx で Dialog インポート・使用に切り替え**
```bash
# 対象: frontend/src/App.tsx
# 変更内容:
# 1. import { EasyModeDialog } from '@/components/dialogs/EasyModeDialog'; (既存確認)
# 2. import { ImportChapterDialog } from '@/components/dialogs/ImportChapterDialog'; (追加)
# 3. JSX内で ImportChapterDialog を使用するよう修正
```
**App.tsx 修正箇所（行310-317付近）:**
```tsx
// 既存の EasyModeDialog はそのまま
{isCreateModalOpen && (
  <EasyModeDialog
    isOpen={isCreateModalOpen}
    onClose={() => setCreateModalOpen(false)}
    onSubmit={handleCreateEasyMode}
/>
)}

// 新規追加: ImportChapterDialog
// useWritingStore から importEpNum, importText, importDoRefine, setImportEpNum, setImportText, setImportDoRefine を取得
// 状態管理用のローカル state を用意して Dialog に渡す
```

**構文チェック**: `cd frontend && npx tsc --noEmit`

---

### フェーズA-4: App.tsx 再構成・タイポ修正（ステップ11-16）

#### **ステップ11: App.tsx の typo 修正（ビルドブロッカー解消）**
```bash
# 対象: frontend/src/App.tsx
# 修正対象（IMPLEMENTATION_STATUS_AND_PLAN.md 記載）:
```
**修正一覧:**
| 修正前 | 修正後 | 場所目安 |
|--------|--------|----------|
| `setBile` | `setBible` | 行108, 232 |
| `bier` | `bible` | 行265 (WriteTab props) |
| `selectBook` | `selectedBook` | 行135 |
| `handleImportChannel` | `handleImportChapter` | 該当行検索 |
| `useUserStore` | `useBookStore` | 行66 |

**確認**: `cd frontend && npx tsc --noEmit` でエラー0件

---

#### **ステップ12: useBookDetails hook を App.tsx で使用**
```bash
# 対象: frontend/src/App.tsx
# アクション: loadBookDetails 関数（行99-126）を削除し、useBookDetails hook を使用
```
**変更内容:**
```typescript
// import 追加（行41付近）
import { useBookDetails } from '@/hooks/useBookDetails';

// App.tsx 内で loadBookDetails を削除し、代わりに hook を使用
const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null, activeTab);

// useEffect 内で呼び出し
useEffect(() => {
  if (selectedBook) {
    loadBookDetails(selectedBook.id);
  }
}, [selectedBook, activeTab, loadBookDetails]);
```

**構文チェック**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ13: useTaskStream hook を App.tsx で使用**
```bash
# 対象: frontend/src/App.tsx
# アクション: SSE接続制御用の useEffect（行147-177）を削除し、useTaskStream hook を使用
```
**変更内容:**
```typescript
// import 追加
import { useTaskStream } from '@/hooks/useTaskStream';

// App.tsx 内
const { activeTaskId, taskStatus } = useTaskStore(); // 既存

// useTaskStream を呼び出し
useTaskStream(activeTaskId, {
  onStatus: setTaskStatus,
  onComplete: (status) => {
    setActiveTaskId(null);
    if (selectedBook) loadBookDetails(selectedBook.id);
    if (status.error) toast.error(`タスクエラー: ${status.error}`);
    else toast.success('バックグラウンドタスクが完了しました！');
  },
  onError: (error) => console.error('Task stream error:', error),
});

// 自動スクロール用 useEffect は useTaskMonitor に移動済みなので削除
```

**構文チェック**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ14: useTaskMonitor hook を App.tsx で使用**
```bash
# 対象: frontend/src/App.tsx
# アクション: TaskMonitor コンポーネントへの props 渡しを hook 経由に
```
**変更内容:**
```typescript
// import 追加
import { useTaskMonitor } from '@/hooks/useTaskMonitor';

// App.tsx 内
const { logEndRef, handleStopTask } = useTaskMonitor();

// JSX で TaskMonitor に渡す
{activeTaskId && taskStatus && (
  <TaskMonitor
    logEndRef={logEndRef}
    onStop={handleStopTask}
  />
)}
```

**構文チェック**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ15: 残存ハンドラを useAppActions 経由に統一確認**
```bash
# 対象: frontend/src/App.tsx
# 確認: handleCreateEasyMode, handleTriggerWriting, handleExpandPlots, 
#       handleCritiqueOptimize, handleImportChapter, handleGenerateMarketing
#       が全て useAppActions から取得されて使用されているか
```
**確認ポイント**: 行194-202 の `useAppActions` 戻り値の destructuring に全ハンドラが含まれているか  
**不足があれば**: `useAppActions.ts` に追加実装

**構文チェック**: `cd frontend && npx tsc --noEmit`

---

#### **ステップ16: フロントエンドビルド・動作確認**
```bash
cd frontend && npm run build
# 成功したら
cd frontend && npm run dev
# ブラウザで http://localhost:5173 確認
```
**チェックリスト:**
- [ ] 4タブ切り替え動作
- [ ] イージーモードダイアログ開閉・送信
- [ ] 章取り込みダイアログ開閉・送信
- [ ] タスクモニター表示/停止
- [ ] 執筆実行、プロット展開、品質分析、マーケティング生成

---

## 📦 Phase B: CORS設定の制限（12ステップ）

### フェーズB-1: 設定ファイル完全化（ステップ17-20）

#### **ステップ17: config/settings.py を Pydantic BaseSettings 完全対応に更新**
```bash
# 対象: /workspaces/autonovel/config/settings.py
# 現状: ConfigManager と Settings が併存（Settings 未使用）
# アクション: Settings クラスを実用化し、CORS設含む全設定を一元管理
```
**実装内容:**
```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # CORS設定
    cors_allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:8501"]
    
    # データベース
    database_url: str = "sqlite:///./autonovel.db"
    
    # API設定
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # ログ設定
    log_level: str = "INFO"
    
    # その他既存設定をここに統合
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# 後方互換性のため ConfigManager も残す（段階的移行）
```

**依存関係追加**: `cd /workspaces/autonovel && pip install pydantic-settings`

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile config/settings.py`

---

#### **ステップ18: config/cors_config.py を settings.py 経由で取得するよう修正**
```bash
# 対象: /workspaces/autonovel/config/cors_config.py
# アクション: get_settings() を使用して CORS 許可 origin を取得
```
**修正内容:**
```python
# config/cors_config.py
from config.settings import get_settings

def get_allowed_origins() -> List[str]:
    """環境変数からCORS許可originリストを取得"""
    settings = get_settings()
    return settings.cors_allowed_origins
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile config/cors_config.py`

---

#### **ステップ19: .env.example に CORS 設定追加確認**
```bash
# 対象: /workspaces/autonovel/.env.example
# 確認: CORS_ALLOWED_ORIGINS が定義済みか
# 未定義なら追加
```
**期待内容:**
```env
# CORS Configuration
CORS_ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:8501"]

# Database
DATABASE_URL=sqlite:///./autonovel.db

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

---

#### **ステップ20: CORS設定読み込みテスト作成・実行**
```bash
# 対象: /workspaces/autonovel/tests/test_cors_config.py (新規作成)
```
**テスト内容:**
```python
# tests/test_cors_config.py
import os
import pytest

def test_get_allowed_origins_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://localhost:3000","http://localhost:8000"]')
    # 環境変数設定後にインポート（キャッシュ対策）
    import importlib
    import config.cors_config
    importlib.reload(config.cors_config)
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://localhost:3000" in origins
    assert "http://localhost:8000" in origins

def test_get_allowed_origins_default(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    import importlib
    import config.cors_config
    importlib.reload(config.cors_config)
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://localhost:5173" in origins
    assert "http://localhost:8501" in origins

def test_get_allowed_origins_comma_separated(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://a.com,http://b.com")
    import importlib
    import config.cors_config
    importlib.reload(config.cors_config)
    from config.cors_config import get_allowed_origins
    origins = get_allowed_origins()
    assert "http://a.com" in origins
    assert "http://b.com" in origins
```

**実行**: `cd /workspaces/autonovel && python -m pytest tests/test_cors_config.py -v`  
**完了条件**: 3テスト全 PASSED

---

### フェーズB-2: 動作確認・テスト（ステップ21-24）

#### **ステップ21: 開発環境での CORS 動作確認（curlテスト）**
```bash
# ターミナル1: バックエンド起動
cd /workspaces/autonovel && python -m uvicorn src.backend.server:app --reload --port 8000

# ターミナル2: curlテスト実行
# 許可origin
curl -I -X OPTIONS http://localhost:8000/health -H "Origin: http://localhost:5173"
# 期待: Access-Control-Allow-Origin: http://localhost:5173

# 非許可origin
curl -I -X OPTIONS http://localhost:8000/health -H "Origin: http://malicious-site.com"
# 期待: Access-Control-Allow-Origin ヘッダーなし（または異なるorigin）

# バックエンド停止: Ctrl+C
```

**完了条件**: 許可originでヘッダー返却、非許可で拒否

---

#### **ステップ22: 本番環境想定テスト**
```bash
# 環境変数で本番origin指定して起動
CORS_ALLOWED_ORIGINS='["https://prod.example.com"]' python -m uvicorn src.backend.server:app --reload --port 8000 &

# テスト
curl -I -X OPTIONS http://localhost:8000/health -H "Origin: https://prod.example.com"
# 期待: 許可される

curl -I -X OPTIONS http://localhost:8000/health -H "Origin: https://evil.com"
# 期待: 拒否される

# プロセス停止
pkill -f uvicorn
```

---

#### **ステップ23: CORS エンドポイント統合テスト作成・実行**
```bash
# 対象: /workspaces/autonovel/tests/test_cors_endpoints.py (新規作成)
```
**テスト内容:**
```python
# tests/test_cors_endpoints.py
from fastapi.testclient import TestClient
from src.backend.server import app

client = TestClient(app)

def test_cors_headers_in_response():
    response = client.get("/health")
    # FastAPI TestClient は CORS ヘッダーを自動付与しないため、OPTIONS でテスト
    response = client.options("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"

def test_cors_rejects_unauthorized_origin():
    response = client.options("/health", headers={"Origin": "http://evil.com"})
    # 未許可originの場合、CORSヘッダーが含まれないか、異なるoriginが返る
    assert response.headers.get("Access-Control-Allow-Origin") != "http://evil.com"
```

**実行**: `cd /workspaces/autonovel && python -m pytest tests/test_cors_endpoints.py -v`  
**完了条件**: 2テスト全 PASSED

---

#### **ステップ24: 全バックエンドテスト実行**
```bash
cd /workspaces/autonovel && python -m pytest tests/ -v --tb=short -k "cors or CORS"
# CORS関連テストのみ先に確認

cd /workspaces/autonovel && python -m pytest tests/ -v --tb=short
# 全テスト実行
```
**完了条件**: 全テスト PASSED（既存テストが壊れていないこと確認）

---

## 📦 Phase C: Streamlit状態管理の統一（20ステップ）

### フェーズC-1: 現状分析・基盤強化（ステップ25-30）

#### **ステップ25: st.session_state 直接使用箇所の全量調査**
```bash
cd /workspaces/autonovel && grep -rn "st\.session_state\." streamlit_app/ --include="*.py" | grep -v "state.py" | grep -v "stores/" | grep -v "__pycache__"
```
**アクション**: 出力を `docs/session_state_usage_audit.md` に保存・分類  
**分類項目**:
- 永続化必要: apiKey, selectedBookId, userSettings 等
- 一時的（画面遷移で破棄OK）: UI表示状態、フォーム入力値 等

---

#### **ステップ26: 状態使用パターン分類ドキュメント化**
```bash
# 上記grep結果を整理して docs/state_migration_analysis.md 作成
```
**テンプレート:**
```markdown
# Streamlit 状態移行分析

## 永続化必要（SessionStore/UIStateStore経由）
- api_key → SessionStore
- selected_book_id → SessionStore
- user_preferences → SessionStore

## 一時的（UIStateStore経由）
- form_data (各種フォーム入力値)
- show_modal, active_tab 等のUIフラグ
- search_query, filter_settings

## 移行対象ファイル（優先順）
1. ui_tabs_writing.py - 大量の st.session_state 直接使用
2. ui_tabs_planning.py - UIStateStore 部分使用、直接使用混在
3. sidebar.py - SessionStore 使用済みだが一部直接使用
4. progress.py - 要確認
5. ui_tabs_analytics.py - 要確認
6. ui_tabs_monitor.py - 要確認
7. ui_tabs_audit.py - 要確認
```

---

#### **ステップ27: バックアップ取得**
```bash
cp streamlit_app/state.py streamlit_app/state.py.backup
cp streamlit_app/app.py streamlit_app/app.py.backup
cp streamlit_app/ui_tabs_writing.py streamlit_app/ui_tabs_writing.py.backup
cp streamlit_app/ui_tabs_planning.py streamlit_app/ui_tabs_planning.py.backup
```

---

#### **ステップ28: UIStateStore に移行ヘルパー追加**
```bash
# 対象: streamlit_app/state.py
# 追加: SessionManager に migrate_from_session メソッド（未実装なら）
```
**実装内容（state.py の SessionManager クラス内に追加）:**
```python
@classmethod
def migrate_from_session(cls, key: str, default: Any = None) -> Any:
    """st.session_state から値を取得してUIStateStoreに移行"""
    import streamlit as st
    from streamlit_app.state_keys import UI_STATE_KEY
    
    # UIStateStore が初期化済みか確認
    if UI_STATE_KEY not in st.session_state:
        # 初期化をトリガー
        _ = UIStateStore().ui_state
    
    if key in st.session_state:
        value = st.session_state[key]
        del st.session_state[key]  # 移行後に削除
        # UIStateStore の form_data に格納
        ui_state = st.session_state[UI_STATE_KEY]
        ui_state.form_data[key] = value
        return value
    return default
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/state.py`

---

#### **ステップ29: UIStateStore にサブスクリプション機能追加**
```bash
# 対象: streamlit_app/state.py
# 追加: UIStateStore クラスに subscribe/_notify_subscribers
```
**実装内容（UIStateStore クラス内に追加）:**
```python
# クラス変数として追加
_subscribers: dict[str, list[Callable]] = {}

@classmethod
def subscribe(cls, key: str, callback: Callable) -> Callable:
    """状態変更時のコールバック登録"""
    if key not in cls._subscribers:
        cls._subscribers[key] = []
    cls._subscribers[key].append(callback)
    return lambda: cls._subscribers[key].remove(callback)  # アンサブスクライブ用

@classmethod
def _notify_subscribers(cls, key: str, value: Any) -> None:
    for callback in cls._subscribers.get(key, []):
        try:
            callback(value)
        except Exception:
            pass  # コールバックエラーは握りつぶす

# update_ui_state 内で通知を呼び出すよう修正
def update_ui_state(self, **kwargs) -> None:
    state = self.ui_state
    for key, value in kwargs.items():
        if hasattr(state, key):
            setattr(state, key, value)
        else:
            state.form_data[key] = value
        # 変更通知
        self._notify_subscribers(key, value)
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/state.py`

---

#### **ステップ30: UIStateStore テストファイル作成・実行**
```bash
# 対象: /workspaces/autonovel/tests/test_ui_state_store.py (新規作成)
```
**テスト内容:**
```python
# tests/test_ui_state_store.py
import pytest
import streamlit as st
from streamlit_app.state import UIStateStore, UIState

def test_ui_state_initialization():
    runtime = UIStateStore.get_runtime()
    assert isinstance(runtime.ui_state, UIState)
    assert runtime.ui_state.show_modal == False
    assert runtime.ui_state.easy_genre == 'ダークファンタジー'

def test_update_ui_state():
    store = UIStateStore()
    store.update_ui_state(show_modal=True, custom_key="test_value")
    assert store.get_ui_state_value("show_modal") == True
    assert store.get_ui_state_value("custom_key") == "test_value"

def test_subscribe_notify():
    store = UIStateStore()
    called = []
    def callback(val):
        called.append(val)
    
    unsubscribe = UIStateStore.subscribe("test_key", callback)
    store.update_ui_state(test_key="hello")
    assert called == ["hello"]
    
    # アンサブスクライブ確認
    unsubscribe()
    store.update_ui_state(test_key="world")
    assert called == ["hello"]  # 追加されない
```

**実行**: `cd /workspaces/autonovel && python -m pytest tests/test_ui_state_store.py -v`  
**完了条件**: 3テスト全 PASSED

---

### フェーズC-2: コンポーネント移行（ステップ31-38）

> **共通手順（各ファイル共通）:**
> 1. `from streamlit_app.state import get_ui_state, update_ui_state` をインポート追加
> 2. `st.session_state['key']` → `get_ui_state().key` または `get_ui_state().form_data.get('key')`
> 3. `st.session_state.key = value` → `update_ui_state(key=value)`
> 4. 動作確認

---

#### **ステップ31: ui_tabs_writing.py 移行（最優先・最大）**
```bash
# 対象: streamlit_app/ui_tabs_writing.py
# 重点移行対象（ファイル冒頭の st.session_state 直接使用）:
# - commercial_task_id
# - report_generated
# - api_retry_state
# - poll_interval
# - gen_task_id
# - import_ep_num, import_text, import_do_refine 等のフォーム状態
```
**移行パターン:**
```python
# 修正前
if "commercial_task_id" not in st.session_state:
    st.session_state.commercial_task_id = None

# 修正後
from streamlit_app.state import get_ui_state, update_ui_state
ui_state = get_ui_state()
if not hasattr(ui_state, 'commercial_task_id'):
    update_ui_state(commercial_task_id=None)

# 使用箇所
# 修正前: st.session_state.commercial_task_id = task_id
# 修正後: update_ui_state(commercial_task_id=task_id)

# 修正前: st.session_state.commercial_task_id
# 修正後: get_ui_state().commercial_task_id
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/ui_tabs_writing.py`

---

#### **ステップ32: ui_tabs_planning.py 移行**
```bash
# 対象: streamlit_app/ui_tabs_planning.py
# 重点: 
# - easy_genre, easy_keywords, easy_archetype, easy_target_eps, easy_word_count, easy_concept
# - wizard_state 関連
# ※ 既に UIStateStore を部分使用しているため差分移行
```
**確認ポイント**: `UIStateStore.get_runtime().easy_genre_key` 等の既存アクセスパターンと整合性

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/ui_tabs_planning.py`

---

#### **ステップ33: sidebar.py 移行**
```bash
# 対象: streamlit_app/sidebar.py
# 重点: APIキー管理 (runtime.api_key 等)
# ※ SessionManager 経由で AppStateModel を使用中だが、一部直接アクセス残存の可能性
```
**移行対象**: `st.session_state.api_key` 等があれば `SessionManager.get_state().config.api_key` 経由に統一

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/sidebar.py`

---

#### **ステップ34: progress.py 移行**
```bash
# 対象: streamlit_app/progress.py
# 確認: st.session_state 直接使用箇所を全て UIStateStore/SessionStore 経由に
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/progress.py`

---

#### **ステップ35: ui_tabs_analytics.py 移行**
```bash
# 対象: streamlit_app/ui_tabs_analytics.py
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/ui_tabs_analytics.py`

---

#### **ステップ36: ui_tabs_monitor.py 移行**
```bash
# 対象: streamlit_app/ui_tabs_monitor.py
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/ui_tabs_monitor.py`

---

#### **ステップ37: ui_tabs_audit.py 移行**
```bash
# 対象: streamlit_app/ui_tabs_audit.py
```

**構文チェック**: `cd /workspaces/autonovel && python -m py_compile streamlit_app/ui_tabs_audit.py`

---

#### **ステップ38: 残りファイルの grep 再確認・残存修正**
```bash
cd /workspaces/autonovel && grep -rn "st\.session_state\." streamlit_app/ --include="*.py" | grep -v "state.py" | grep -v "stores/" | grep -v "__pycache__" | grep -v ".backup"
```
**完了条件**: 出力が0行（state.py, stores/ 以外で直接使用なし）

---

### フェーズC-3: 統合テスト・最終確認（ステップ39-48）

#### **ステップ39: Streamlitアプリ起動テスト**
```bash
cd /workspaces/autonovel
timeout 30 streamlit run streamlit_app/app.py --server.headless true --server.port 8501 || true
# エラーなく起動プロセスが始まることを確認（30秒でタイムアウト）
```

---

#### **ステップ40: Streamlit状態遷移テスト作成・実行**
```bash
# 対象: /workspaces/autonovel/tests/test_streamlit_state.py (拡充)
```
**テスト追加:**
```python
# tests/test_streamlit_state.py 追加分
def test_state_persistence_across_reruns():
    """Streamlit rerun間で状態が保持されることを確認"""
    from streamlit_app.state import UIStateStore
    runtime = UIStateStore.get_runtime()
    initial_subscribers = len(UIStateStore._subscribers)
    
    # 大量サブスクライブ・アンサブスクライブ
    for i in range(100):
        unsubscribe = UIStateStore.subscribe(f"test_key_{i}", lambda x: x)
        unsubscribe()  # 即座に解除
    
    # サブスクライバーが蓄積されていないか確認
    assert len(UIStateStore._subscribers) == initial_subscribers
```

**実行**: `cd /workspaces/autonovel && python -m pytest tests/test_streamlit_state.py -v`  
**完了条件**: テスト全 PASSED、メモリリークなし

---

#### **ステップ41: メモリリークチェック（サブスクリプション蓄積確認）**
```bash
# ステップ40のテスト実行で確認済みだが、明示的に実行
cd /workspaces/autonovel && python -m pytest tests/test_streamlit_state.py::test_state_persistence_across_reruns -v
```

---

#### **ステップ42: CommercialPipeline 単体テスト修正・実行（Phase 1 連携）**
```bash
# commercial_pipeline.py の step_plan エラーテスト修正（COMMERCIAL_PIPELINE_72STEP_PLAN Phase 1）
cd /workspaces/autonovel && python -m pytest tests/test_commercial_pipeline_error.py -v
```
**完了条件**: 2テスト全 PASSED

---

#### **ステップ43: CommercialPipeline 全単体テスト実行**
```bash
cd /workspaces/autonovel && python -m pytest tests/test_commercial_pipeline_unit.py -v
```
**完了条件**: 全テスト PASSED

---

#### **ステップ44: フロントエンド全テスト実行**
```bash
cd /workspaces/autonovel/frontend && npm run build
# ビルド成功確認

# 必要に応じてテスト実行（package.json に test スクリプトがあれば）
# npm test
```

---

#### **ステップ45: バックエンド全テスト実行**
```bash
cd /workspaces/autonovel && python -m pytest tests/ -v --tb=short --ignore=tests/test_streamlit_state.py
# Streamlitテスト除く全バックエンドテスト
```
**完了条件**: 全テスト PASSED

---

#### **ステップ46: リンター・型チェック全実行**
```bash
# フロントエンド
cd /workspaces/autonovel/frontend && npx tsc --noEmit

# バックエンド
cd /workspaces/autonovel && python -m ruff check src/ config/ tests/
cd /workspaces/autonovel && python -m mypy src/ config/ --ignore-missing-imports

# Streamlit
cd /workspaces/autonovel && python -m ruff check streamlit_app/
```

**完了条件**: 全チェック通過（warning は許容、error は0件）

---

#### **ステップ47: ドキュメント更新**
```bash
# 対象: docs/CORS_CONFIG.md (作成または更新)
# 対象: docs/STREAMLIT_STATE_MIGRATION.md (作成)
# 対象: docs/FINAL_CHECKLIST.md (作成)
```

**CORS_CONFIG.md 内容:**
```markdown
# CORS設定ガイド

## 環境変数
- `CORS_ALLOWED_ORIGINS`: カンマ区切りまたはJSON配列で許可originリスト
  - 開発環境: `http://localhost:5173,http://localhost:8501`
  - 本番環境: `https://your-production-domain.com`

## 設定ファイル
- `config/cors_config.py`: 許可origin取得ロジック
- `config/settings.py`: Pydantic Settings での定義
- `src/backend/server.py`: CORS middleware 設定

## 動作確認
```bash
# 開発環境
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8501 python -m uvicorn src.backend.server:app --reload

# curlで確認
curl -I -X OPTIONS http://localhost:8000/health -H "Origin: http://localhost:5173"
# Access-Control-Allow-Origin ヘッダーが返ることを確認
```
```

---

#### **ステップ48: 最終動作確認チェックリスト実行・完了マーク**
```bash
# 対象: docs/FINAL_CHECKLIST.md 作成・実行
```

**FINAL_CHECKLIST.md:**
```markdown
# 最終動作確認チェックリスト

## React Frontend (Phase A)
- [ ] npm run build 成功
- [ ] npm run dev 起動成功
- [ ] 4タブ切り替え動作
- [ ] イージーモードダイアログ開閉・送信
- [ ] 章取り込みダイアログ開閉・送信
- [ ] タスクモニター表示/停止
- [ ] 執筆実行、プロット展開、品質分析、マーケティング生成
- [ ] npx tsc --noEmit エラー0件

## Backend CORS (Phase B)
- [ ] curl テスト通過 (許可origin: http://localhost:5173)
- [ ] curl テスト通過 (許可origin: http://localhost:8501)
- [ ] curl テスト通過 (拒否origin: http://malicious-site.com)
- [ ] 単体テスト通過 (test_cors_config.py)
- [ ] 統合テスト通過 (test_cors_endpoints.py)
- [ ] 全バックエンドテスト通過
- [ ] docker-compose.yml 環境変数対応確認
- [ ] Dockerfile 確認

## Streamlit State (Phase C)
- [ ] streamlit run 起動成功 (エラーなし)
- [ ] st.session_state 直接使用箇所ゼロ (state.py, stores/ 除く)
- [ ] UIStateStore 経由で全状態管理
- [ ] 状態永続化/復元動作
- [ ] メモリリークなし (サブスクリプション蓄積なし)
- [ ] test_ui_state_store.py 全パス
- [ ] test_streamlit_state.py 全パス

## CommercialPipeline
- [ ] test_commercial_pipeline_error.py 全パス
- [ ] test_commercial_pipeline_unit.py 全パス

## 全体
- [ ] 全テストパス (frontend + backend + streamlit)
- [ ] バックアップファイル削除 (.backup ファイル)
- [ ] リンター・型チェック全通過
```

---

## 🛠️ 開発環境セットアップ確認コマンド

```bash
# フロントエンド
cd /workspaces/autonovel/frontend
npm install --legacy-peer-deps
npx tsc --noEmit
npm run build

# バックエンド
cd /workspaces/autonovel
pip install pydantic-settings
python -m pytest tests/test_cors_config.py -v

# Streamlit
streamlit run streamlit_app/app.py --server.headless true
```

---

## ⚠️ 既知の問題・注意点（実装前必読）

1. **App.tsx の typo 多数** - ステップ11で一括修正必須（`setBile`/`bier`/`selectBook`/`handleImportChannel`/`useUserStore`）
2. **useUIStore に setter 不足** - `setOptHistory`, `setPendingPatches`, `setPromptVersions`, `setMetricTrend` をステップ4で追加必須
3. **config/settings.py** - Pydantic BaseSettings への完全移行が必要（現在は ConfigManager 併用）
4. **Streamlit st.session_state 直接使用** - 大量残存の可能性、ステップ25で全量把握必須
5. **テストファイル未整備** - 各ステップでテスト作成を含めること
6. **commercial_pipeline.py** - `_step_plan` のキーワードバリデーションは適用済み（ステップ4完了済み）だが、テストが通るかステップ42で確認必要

---

## 📅 推奨実行順序（依存関係考慮）

| 実行順 | ステップ範囲 | 理由 |
|--------|-------------|------|
| 1 | **A1-A3** (型定義) | 全ての基盤 |
| 2 | **A4-A6** (hooks整備) | ロジック分離の核心 |
| 3 | **A7-A10** (Dialog) | UI完成に必須 |
| 4 | **A11-A16** (App.tsx再構成) | 統合・動作確認の前提 |
| 5 | **B17-B20** (CORS設定完全化) | セキュリティ要件 |
| 6 | **B21-B24** (CORS動作確認) | 実環境検証 |
| 7 | **C25-C30** (現状分析・基盤強化) | 移行前提の整理 |
| 8 | **C31-C38** (コンポーネント移行) | 実質的な統一 |
| 9 | **C39-C48** (統合テスト・最終確認) | 最終確認 |

---

## ✅ 完了条件

全48ステップが完了し、以下が満たされていること：
1. `npm run build` 成功（フロントエンド）
2. `python -m pytest tests/ -v` 全パス（バックエンド＋Streamlit）
3. `streamlit run streamlit_app/app.py --server.headless true` エラーなし起動
4. CORS curlテスト 許可/拒否両方正常
5. 全リンター・型チェック通過
6. `.backup` ファイル削除済み

---

*作成日: 2026-07-14*  
*検証基準: IMPLEMENTATION_STATUS_AND_PLAN.md + COMMERCIAL_PIPELINE_72STEP_PLAN_DETAILED.md 統合・最適化版*  
*想定実装時間: 20-27時間（各ステップ30分以内）*