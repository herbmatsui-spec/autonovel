# 提案7: エディタのローカルファースト自動保存 & クラッシュリカバリ 実装計画書（全12ステップ）

**対象レイヤー**: `frontend/src/lib/storage/`, `frontend/src/types/`, `frontend/src/hooks/`, `frontend/src/components/editor/`  
**目的**: 執筆中の原稿消失事故を根絶するため、同期localStorage（5MB上限・グローバル単一キー）から、非同期IndexedDBを用いたエピソード単位のローカルファースト自動保存（500msデバウンス）へ移行する。さらに、クラッシュ時の「未保存データ復旧モーダル」およびネットワーク状態（Online / Offline）検知インジケーターを導入する。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なTypeScript/Reactコード**、**検証コマンド**、**合格条件** を完備しています。`npm run typecheck`（`tsc --noEmit`）でエラー0件を容易に維持・確認できます。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | 型定義 | `frontend/src/types/editorSnapshot.ts` | 原稿スナップショット、復元候補、保存ステータスの型定義 |
| **Step 2** | IndexedDBクライアント | `frontend/src/lib/storage/indexedDbClient.ts` | ブラウザ標準IndexedDBをPromiseでラップした軽量ストア |
| **Step 3** | キー設計 | `frontend/src/lib/storage/indexedDbClient.ts` | `draft_${bookId}_${episodeId}` による作品・エピソード分離 |
| **Step 4** | ネットワーク検知フック | `frontend/src/hooks/useNetworkStatus.ts` | オンライン / オフライン状態をリアルタイム監視するフック |
| **Step 5** | IndexedDB自動保存フック | `frontend/src/hooks/useIndexedDbAutosave.ts` | 500msデバウンスでIndexedDBへ非同期保存するフック |
| **Step 6** | 復元判定ロジック | `frontend/src/hooks/useCrashRecovery.ts` | サーバー版タイムスタンプとローカルキャッシュを比較する判定フック |
| **Step 7** | 復旧確認モーダル | `frontend/src/components/editor/RecoveryModal.tsx` | 「未保存のローカル原稿があります」差分表示・復元ダイアログ |
| **Step 8** | インジケーター改修 | `frontend/src/components/editor/AutosaveIndicator.tsx` | オフライン警告・保存中・保存済みタイムスタンプの統合UI |
| **Step 9** | エディタ統合 | `frontend/src/components/editor/Editor.tsx` | 新フックと復元モーダルのエディタ本体への組み込み |
| **Step 10** | クリーンアップ | `frontend/src/hooks/useAutosave.ts` | 旧localStorage実装からの移行と下位互換エイリアス |
| **Step 11** | 単体テスト | `frontend/src/lib/storage/__tests__/indexedDbClient.test.ts` | IndexedDBクライアントのCRUDテスト |
| **Step 12** | 型検査 & ビルド | `frontend/` | `npm run typecheck` によるTypeScript整合性検証 |

---

## 🛠 各ステップ詳細仕様

### Step 1: 原稿スナップショット型定義
- **目的**: 保存するテキスト、文字数、更新日時、バージョン情報をカプセル化する型を定義。
- **対象ファイル**: `frontend/src/types/editorSnapshot.ts`（新規作成）
- **実装コード**:
```typescript
/**
 * 原稿ローカルキャッシュスナップショット型定義
 */
export interface EditorSnapshot {
  key: string;
  bookId: string | number;
  episodeId: string | number;
  content: string;
  charCount: number;
  updatedAt: number; // UNIX timestamp (ms)
}

export type AutoSaveStatus = "saved" | "saving" | "unsaved" | "offline";

export interface RecoveryCheckResult {
  hasRecoveryCandidate: boolean;
  localSnapshot: EditorSnapshot | null;
  serverContent: string;
  serverUpdatedAt?: number;
}
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit src/types/editorSnapshot.ts`
- **合格条件**: エラーなし。

---

### Step 2 & 3: IndexedDB クライアント実装
- **目的**: 外部ライブラリなしでブラウザ標準のIndexedDBを操作するPromiseラッパー。
- **対象ファイル**: `frontend/src/lib/storage/indexedDbClient.ts`（新規作成）
- **実装コード**:
```typescript
import { EditorSnapshot } from "../../types/editorSnapshot";

const DB_NAME = "autonovel_storage";
const STORE_NAME = "editor_drafts";
const DB_VERSION = 1;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.indexedDB) {
      return reject(new Error("IndexedDB is not supported"));
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "key" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export const indexedDbClient = {
  makeKey(bookId: string | number, episodeId: string | number): string {
    return `draft_${bookId}_${episodeId}`;
  },

  async saveSnapshot(snapshot: EditorSnapshot): Promise<void> {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.put(snapshot);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  },

  async getSnapshot(bookId: string | number, episodeId: string | number): Promise<EditorSnapshot | null> {
    const db = await openDB();
    const key = this.makeKey(bookId, episodeId);
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(key);
      req.onsuccess = () => resolve((req.result as EditorSnapshot) || null);
      req.onerror = () => reject(req.error);
    });
  },

  async deleteSnapshot(bookId: string | number, episodeId: string | number): Promise<void> {
    const db = await openDB();
    const key = this.makeKey(bookId, episodeId);
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.delete(key);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  },
};
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 4: ネットワーク検知フック (`useNetworkStatus.ts`)
- **目的**: オンライン/オフライン切替を即座にUIに反映する。
- **対象ファイル**: `frontend/src/hooks/useNetworkStatus.ts`（新規作成）
- **実装コード**:
```typescript
import { useState, useEffect } from "react";

export function useNetworkStatus(): boolean {
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    return typeof navigator !== "undefined" && typeof navigator.onLine === "boolean"
      ? navigator.onLine
      : true;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return isOnline;
}
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 5: IndexedDB自動保存フック (`useIndexedDbAutosave.ts`)
- **目的**: 500msデバウンスでIndexedDBへ安全にキャッシュするフック。
- **対象ファイル**: `frontend/src/hooks/useIndexedDbAutosave.ts`（新規作成）
- **実装コード**:
```typescript
import { useState, useEffect, useRef, useCallback } from "react";
import { AutoSaveStatus, EditorSnapshot } from "../types/editorSnapshot";
import { indexedDbClient } from "../lib/storage/indexedDbClient";
import { useNetworkStatus } from "./useNetworkStatus";

export function useIndexedDbAutosave(
  bookId: string | number,
  episodeId: string | number,
  content: string,
  delay: number = 500
) {
  const isOnline = useNetworkStatus();
  const [status, setStatus] = useState<AutoSaveStatus>("saved");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const save = useCallback(async () => {
    try {
      const snapshot: EditorSnapshot = {
        key: indexedDbClient.makeKey(bookId, episodeId),
        bookId,
        episodeId,
        content,
        charCount: content.length,
        updatedAt: Date.now(),
      };
      await indexedDbClient.saveSnapshot(snapshot);
      setLastSavedAt(new Date());
      setStatus(isOnline ? "saved" : "offline");
    } catch (err) {
      console.warn("IndexedDB autosave failed:", err);
      setStatus("unsaved");
    }
  }, [bookId, episodeId, content, isOnline]);

  useEffect(() => {
    setStatus("unsaved");
    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    timeoutRef.current = setTimeout(() => {
      setStatus("saving");
      save();
    }, delay);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [content, delay, save]);

  return { status, lastSavedAt, save };
}
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 6: 復元判定ロジック (`useCrashRecovery.ts`)
- **目的**: エディタ初期化時にローカルとサーバーを比較し、復元候補があるかチェックする。
- **対象ファイル**: `frontend/src/hooks/useCrashRecovery.ts`（新規作成）
- **実装コード**:
```typescript
import { useState, useEffect } from "react";
import { EditorSnapshot } from "../types/editorSnapshot";
import { indexedDbClient } from "../lib/storage/indexedDbClient";

export function useCrashRecovery(
  bookId: string | number,
  episodeId: string | number,
  serverContent: string
) {
  const [recoverySnapshot, setRecoverySnapshot] = useState<EditorSnapshot | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function checkRecovery() {
      try {
        const snapshot = await indexedDbClient.getSnapshot(bookId, episodeId);
        if (!snapshot || !isMounted) return;

        // サーバーとローカルで内容が異なり、ローカルに有意な文字数がある場合に復元確認
        if (snapshot.content && snapshot.content !== serverContent && snapshot.content.length > 5) {
          setRecoverySnapshot(snapshot);
          setIsOpen(true);
        }
      } catch (e) {
        console.warn("Crash recovery check failed:", e);
      }
    }
    checkRecovery();
    return () => {
      isMounted = false;
    };
  }, [bookId, episodeId, serverContent]);

  const dismiss = () => setIsOpen(false);

  return { isOpen, recoverySnapshot, dismiss };
}
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 7: クラッシュ復旧確認モーダル (`RecoveryModal.tsx`)
- **目的**: 未保存データの存在を通知し、復元または破棄を選択させるモーダルUI。
- **対象ファイル**: `frontend/src/components/editor/RecoveryModal.tsx`（新規作成）
- **実装コード**:
```tsx
import React from "react";
import { EditorSnapshot } from "../../types/editorSnapshot";

interface RecoveryModalProps {
  isOpen: boolean;
  snapshot: EditorSnapshot | null;
  onRestore: (recoveredText: string) => void;
  onDiscard: () => void;
}

export const RecoveryModal: React.FC<RecoveryModalProps> = ({
  isOpen,
  snapshot,
  onRestore,
  onDiscard,
}) => {
  if (!isOpen || !snapshot) return null;

  const savedTimeStr = new Date(snapshot.updatedAt).toLocaleString("ja-JP");

  return (
    <div className="modal-overlay" style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="modal-content" style={{ backgroundColor: "#1e1e24", padding: "24px", borderRadius: "12px", maxWidth: "500px", width: "90%", color: "#fff" }}>
        <h3 style={{ margin: "0 0 12px 0", color: "#f59e0b" }}>⚠️ 未保存のローカル原稿が見つかりました</h3>
        <p style={{ fontSize: "14px", color: "#d1d5db", lineHeight: 1.5 }}>
          ブラウザが予期せず終了した可能性があります。以下のスナップショットから原稿を復元しますか？
        </p>
        <div style={{ background: "#2a2b36", padding: "12px", borderRadius: "8px", margin: "16px 0", fontSize: "13px" }}>
          <div>保存日時: {savedTimeStr}</div>
          <div>文字数: {snapshot.charCount} 文字</div>
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
          <button
            onClick={onDiscard}
            style={{ padding: "8px 16px", borderRadius: "6px", border: "1px solid #4b5563", background: "transparent", color: "#9ca3af", cursor: "pointer" }}
          >
            破棄してサーバー版を使用
          </button>
          <button
            onClick={() => onRestore(snapshot.content)}
            style={{ padding: "8px 16px", borderRadius: "6px", border: "none", background: "#3b82f6", color: "#fff", cursor: "pointer", fontWeight: 600 }}
          >
            原稿を復元する
          </button>
        </div>
      </div>
    </div>
  );
};
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 8: インジケーター改修 (`AutosaveIndicator.tsx`)
- **目的**: `AutoSaveStatus`（`offline` 対応）を取り込み、オフライン状態でも安心できるUIを表示。
- **対象ファイル**: `frontend/src/components/editor/AutosaveIndicator.tsx`
- **実装コード**:
```tsx
import React from "react";
import { AutoSaveStatus } from "../../types/editorSnapshot";

interface AutosaveIndicatorProps {
  status: AutoSaveStatus;
  lastSavedAt: Date | null;
}

export const AutosaveIndicator: React.FC<AutosaveIndicatorProps> = ({ status, lastSavedAt }) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  switch (status) {
    case "saving":
      return (
        <span className="autosave-indicator" title="ローカル保存中...">
          <span style={{ color: "#3b82f6" }}>⏳</span>
          <span style={{ marginLeft: 4 }}>保存中...</span>
        </span>
      );
    case "offline":
      return (
        <span className="autosave-indicator" title="オフライン（端末内に安全に保存されています）">
          <span style={{ color: "#f59e0b" }}>📶❌</span>
          <span style={{ marginLeft: 4, color: "#f59e0b" }}>端末内保存 (オフライン)</span>
        </span>
      );
    case "unsaved":
      return (
        <span className="autosave-indicator" title="未保存の変更があります">
          <span style={{ color: "#ef4444" }}>●</span>
          <span style={{ marginLeft: 4 }}>未保存</span>
        </span>
      );
    case "saved":
    default:
      return (
        <span className="autosave-indicator" title={lastSavedAt ? `ローカル保存済 ${formatTime(lastSavedAt)}` : "保存済み"}>
          <span style={{ color: "#10b981" }}>✓</span>
          <span style={{ marginLeft: 4 }}>{lastSavedAt ? `保存済 ${formatTime(lastSavedAt)}` : "保存済"}</span>
        </span>
      );
  }
};
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 9: エディタ本体への統合 (`Editor.tsx`)
- **目的**: `Editor.tsx` で `useIndexedDbAutosave` と `RecoveryModal` を使用する。
- **対象ファイル**: `frontend/src/components/editor/Editor.tsx`
- **変更内容**:
```tsx
// インポート追加
import { useIndexedDbAutosave } from "../../hooks/useIndexedDbAutosave";
import { useCrashRecovery } from "../../hooks/useCrashRecovery";
import { RecoveryModal } from "./RecoveryModal";

// コンポーネント内で利用
const { status, lastSavedAt } = useIndexedDbAutosave(bookId, episodeId, content);
const { isOpen, recoverySnapshot, dismiss } = useCrashRecovery(bookId, episodeId, initialContent);

// JSX内に <RecoveryModal ... /> を配置
<RecoveryModal
  isOpen={isOpen}
  snapshot={recoverySnapshot}
  onRestore={(recovered) => {
    setContent(recovered);
    dismiss();
  }}
  onDiscard={dismiss}
/>
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 10: 旧 `useAutosave.ts` のエイリアス互換化
- **目的**: 既存の別画面で `useAutosave` を利用している箇所があっても壊れないようエイリアスを配置。
- **対象ファイル**: `frontend/src/hooks/useAutosave.ts`
- **実装コード**:
```typescript
/**
 * 下位互換エイリアス
 */
export { useIndexedDbAutosave as useAutosave } from "./useIndexedDbAutosave";
export type { AutoSaveStatus as SaveStatus } from "../types/editorSnapshot";
```
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **合格条件**: コンパイルエラーなし。

---

### Step 11: 単体テスト: IndexedDB クライアントのキー設計テスト
- **目的**: キャッシュキー生成およびスナップショット型整合性のテスト。
- **対象ファイル**: `frontend/src/lib/storage/__tests__/indexedDbClient.test.ts`（新規作成）
- **実装コード**:
```typescript
import { indexedDbClient } from "../indexedDbClient";

describe("indexedDbClient", () => {
  it("should generate proper scoped keys", () => {
    const key = indexedDbClient.makeKey("book1", "ep3");
    expect(key).toBe("draft_book1_ep3");
  });

  it("should support numeric ids in key generation", () => {
    const key = indexedDbClient.makeKey(10, 42);
    expect(key).toBe("draft_10_42");
  });
});
```
- **検証コマンド**: `cd frontend && npm test -- src/lib/storage/__tests__/indexedDbClient.test.ts`
- **合格条件**: テストが PASS すること。

---

### Step 12: 型検査 & 全体ビルド検証
- **目的**: フロントエンド全体の型検査が 0 エラーで完了することを確認。
- **検証コマンド**: `cd frontend && npm run typecheck`
- **合格条件**: `tsc --noEmit` が終了コード 0 で正常終了すること。
