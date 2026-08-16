# シーケンス図 - Bible 同期フロー

## 概要
World Bible のライフサイクル同期（承認済み設定のマージ → 最適化 → 整合性監査）フロー。上級者モードで使用。

```mermaid
sequenceDiagram
    autonumber
    actor User as ユーザー (著者/編集者)
    participant API as APIサーバー
    participant Engine as UltimateHegemonyEngine
    participant BibleAgent as WorldBibleGenerator
    participant LLM as LLMゲートウェイ
    participant LLMClient as LLMクライアント
    participant GeminiAPI as Gemini API
    participant DB as データベース
    participant ChromaDB as ChromaDB

    Note over User,API: === 1. 仮設定の提案・承認 ===
    User->>API: POST /api/bible/settings\n{book_id, setting_type, content, status: "proposed"}
    API->>DB: 仮設定として保存 (status="proposed")
    API-->>User: 201 Created
    
    User->>API: POST /api/bible/settings/{id}/resolve\n{status: "approved"}  (または "rejected")
    API->>DB: 仮設定のステータス更新
    API-->>User: 200 OK
    
    Note over User,Engine: === 2. Bible ライフサイクル同期実行 ===
    User->>API: POST /api/bible/sync\n{book_id}
    API->>Engine: engine.sync_bible(book_id, reporter)
    
    Note over Engine,BibleAgent: === Step 1: 承認済み設定のマージ ===
    Engine->>BibleAgent: sync_bible_lifecycle(book_id, reporter)
    BibleAgent->>DB: 承認済み設定 (status="approved") を取得
    BibleAgent->>DB: 既存 Bible (entries, current_bible) を取得
    BibleAgent->>BibleAgent: マージロジック実行\n- 既存エントリとマージ\n- 競合解決 (新規優先/手動解決)\n- バージョン番号インクリメント
    
    Note over BibleAgent,LLM: === Step 2: Bible 最適化 (LLM による整理・圧縮) ===
    BibleAgent->>BibleAgent: 最適化プロンプト構築\n- 現状の Bible 全文\n- 追加された設定\n- 「冗長除去・矛盾解消・構造化」指示
    BibleAgent->>LLM: generate_json(purpose="bible_optimize", prompt, schema=BibleSchema)
    LLM->>LLMClient: get_client("gemini")
    LLMClient->>GeminiAPI: HTTPS generateContent (JSON モード)
    GeminiAPI-->>LLMClient: 構造化 JSON
    LLMClient-->>LLM: 正規化済み
    LLM-->>BibleAgent: 最適化済み Bible Dict
    
    Note over BibleAgent,DB: === Step 3: 整合性監査 ===
    BibleAgent->>BibleAgent: 整合性チェック\n- 設定間の矛盾検出 (キャラ設定 vs プロット等)\n- 必須フィールド存在確認\n- 参照整合性 (キャラ名・用語の統一)
    alt 矛盾検出
        BibleAgent->>DB: 警告ログ記録
        BibleAgent->>Reporter: reporter.report("warning", "矛盾検出: ...")
    end
    
    Note over BibleAgent,DB,ChromaDB: === Step 4: 永続化・ベクトル化 ===
    BibleAgent->>DB: 最適化済み Bible 保存 (current_bible, version, updated_at)
    BibleAgent->>ChromaDB: ベクトル埋め込み更新\n- エントリ単位で埋め込み生成\n- メタデータ (book_id, entry_type, version) 付与
    
    BibleAgent-->>Engine: 同期結果 {success, version, changes_count, warnings}
    Engine-->>API: 同期結果
    API-->>User: 200 OK\n{version: 5, changes: 12, warnings: 0}
    
    Note over User: === 5. 結果確認・手動レビュー ===
    User->>API: GET /api/bible/{book_id}
    API->>DB: 現在の Bible 取得
    API-->>User: Bible 全文 (JSON)
```

## Bible データ構造

```json
{
  "version": 5,
  "updated_at": "2026-08-16T04:00:00Z",
  "entries": {
    "protagonist": {
      "name": "カイト",
      "archetype": "追放された最強",
      "abilities": ["全スキル習得", "魔力無限"],
      "personality": "冷徹だが仲間想い",
      "backstory": "パーティから追放され、復讐を誓う"
    },
    "world": {
      "name": "エルディアナ",
      "magic_system": "スキルベース (習得型)",
      "factions": ["王国", "魔族", "冒険者ギルド"]
    },
    "plot_keys": {
      "betrayal_ep": 2,
      "awakening_ep": 3,
      "musou_start_ep": 4,
      "final_ep": 8
    }
  },
  "metadata": {
    "approved_settings_count": 12,
    "pending_settings_count": 3,
    "last_optimized_at": "2026-08-16T04:00:00Z",
    "optimization_model": "gemini-2.5-pro"
  }
}
```

## 監査チェック項目

| チェック種別 | 内容 | 失敗時 |
|-------------|------|--------|
| 必須フィールド | protagonist.name, world.name, plot_keys 等 | 警告・デフォルト補完 |
| 参照整合性 | キャラ名・用語が全エントリで統一 | 警告・自動修正提案 |
| 矛盾検出 | キャラ能力 vs プロット展開の整合性 | 警告・手動レビュー必須 |
| スキーマ準拠 | JSON Schema (BibleSchema) 準拠 | バリデーションエラー |
| バージョン整合 | version インクリメント・タイムスタンプ | エラー・ロールバック |

## データフロー概要

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────┐
│  仮設定提案  │────▶│  承認/却下   │────▶│  同期実行   │────▶│  完了   │
│  (proposed) │     │  (approved)  │     │  (マージ/最適化/監査/永続化)│  (current_bible) │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  DB 保存     │     │  ChromaDB   │
                    │  (current_bible,│     │  埋め込み更新│
                    │  version, logs)│     │  (ベクトル化) │
                    └──────────────┘     └─────────────┘
```

## 同期トリガー

| トリガー | 条件 | 自動/手動 |
|---------|------|----------|
| 手動実行 | ユーザーが `/api/bible/sync` 呼び出し | 手動 |
| 承認後自動 | 設定承認直後 (Webhook/ポーリング) | 自動 (将来実装) |
| 定期実行 | 1日1回 (cron/Huey スケジューラ) | 自動 (将来実装) |
| 矛盾検出時 | 監査で矛盾検出 → 即時同期 | 自動 (将来実装) |

## パフォーマンス考慮

- **最適化LLM呼び出し**: Bible 全文が長い場合、セクション分割して並列処理 (将来実装)
- **ベクトル埋め込み**: エントリ単位でバッチ処理、ChromaDB の `add` はバッチ対応
- **差分同期**: `updated_at` で変更されたエントリのみ処理 (将来実装)
- **キャッシュ**: 直近の Bible 全文を Redis にキャッシュ (1時間 TTL)