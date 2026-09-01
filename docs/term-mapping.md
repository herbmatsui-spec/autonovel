# Easy Mode Suite 用語・マッピング表

> 対応ドキュメント: [Easy Mode Suite 概要](./easy_mode_suite.md)
> この表は旧コード上の名前と新機能名の対応を記録する。
> 以降の PR・Issue・タスク・コメントでは **機能名（機能 ID）** を使用すること。

---

## 1. 機能名と ID の対応

| 機能名 | 機能 ID（スネークケース） | 旧クラス名 | 旧サービス名 | 旧ファイル名 |
|:--|:--|:--|:--|:--|
| Interactive Writer | `interactive_writer` | — | `execute_generation` (関数) | `src/backend/routers/easy_mode.py` |
| Full Auto Generator | `full_auto` | `EasyModeWorkflow` / `EasyModePipeline` | — | `src/backend/workflows/easy_mode_workflow.py`, `src/easy_mode/pipeline.py` |
| Gacha Pitch | `gacha_pitch` | — | `GachaService` | `src/services/gacha_service.py` |
| Quick Digest | `quick_digest` | — | `DigestService` | `src/services/digest_service.py` |
| Producer Handoff | `producer_handoff` | — | `PromotionService` | `src/services/promotion_service.py` |

---

## 2. コード上の旧名 → 新機能名の置換ルール

### Interactive Writer

| 旧表記 | 新表記 | 備考 |
|:--|:--|:--|
| `EasyModeInput` | （機能名 `Interactive Writer`） | スキーマはそのまま維持 |
| `execute_generation` | `interactive_writer_execute` | 関数リネーム |
| `[easy]` | `[interactive-writer]` | ログプレフィックス |

### Full Auto Generator

| 旧表記 | 新表記 | 備考 |
|:--|:--|:--|
| `EasyModeWorkflow` | `FullAutoWorkflow` | クラス名変更 |
| `EasyModePipeline` | `FullAutoPipeline` | クラス名変更 |
| `[pipeline]` | `[full-auto]` | ログプレフィックス |

### Gacha Pitch

| 旧表記 | 新表記 | 備考 |
|:--|:--|:--|
| `GachaService` | `GachaPitchService` | クラス名変更 |
| `GachaRequest` | （スキーマは維持） | スキーマ名は旧維持 |
| `_GACHA_CACHE` | テーブル `easy_mode_drafts` | Step 8 で永続化 |
| `[gacha]` | `[gacha-pitch]` | ログプレフィックス |

### Quick Digest

| 旧表記 | 新表記 | 備考 |
|:--|:--|:--|
| `DigestService` | `QuickDigestService` | クラス名変更 |
| `_BOOK_STORE` | テーブル `easy_mode_drafts` | Step 8 で永続化 |
| `[digest]` | `[quick-digest]` | ログプレフィックス |

### Producer Handoff

| 旧表記 | 新表記 | 備考 |
|:--|:--|:--|
| `PromotionService` | `ProducerHandoffService` | クラス名変更 |
| `_BOOK_STORE` | テーブル `books.mode` | Step 6 でカラム追加 |
| `[promote]` | `[producer-handoff]` | ログプレフィックス |

---

## 3. ログタグの標準化

ログファイル・SIEM・検索で удобно にフィルタリングするため、次のタグ体系を守る。

| タグ | 出力フォーマット例 | 使用箇所 |
|:--|:--|:--|
| `[interactive-writer]` | `[interactive-writer] Enqueued generation task: task_id=xxx` | `src/backend/routers/easy_mode.py` |
| `[full-auto]` | `[full-auto] EasyModeWorkflow started: genre=...` | `src/backend/workflows/easy_mode_workflow.py` |
| `[gacha-pitch]` | `[gacha-pitch] Plan generation failed (attempt 1/3): ...` | `src/services/gacha_service.py` |
| `[quick-digest]` | `[quick-digest] Digest generation failed for book_id ...` | `src/services/digest_service.py` |
| `[producer-handoff]` | `[producer-handoff] Book data for xxx not found in memory store.` | `src/services/promotion_service.py` |

---

## 4. Issue / PR タイトルの命名規則

```
[<機能 ID>] <簡潔なタイトル>

例:
[interactive-writer] RAG キャッシュヒット率が 60% 以下の場合のフォールバック実装
[gacha-pitch] 3案 LLM 失敗時に固定フォールバック文案の見直し
[producer-handoff] 存在しない book_id で偽データが自動作成される問題の修正
[full-auto] EasyModePipeline のキャンセル制御が未実装
[quick-digest] asyncio.gather 例外時にフォールバックが _BOOK_STORE に保存されない
```

---

## 5. タスクラベルの対応

GitHub Issues / GitLab Labels で次のラベルを使用する。

| ラベル名 | 色 | 対象機能 | 説明 |
|:--|:--|:--|:--|
| `area/interactive-writer` | 青系 | Interactive Writer | 章単位生成パス関連 |
| `area/full-auto` | 緑系 | Full Auto Generator | 全自動生成パス関連 |
| `area/gacha-pitch` | 黄系 | Gacha Pitch | ガチャ企画関連 |
| `area/quick-digest` | 紫系 | Quick Digest | ダイジェスト生成関連 |
| `area/producer-handoff` | 赤系 | Producer Handoff | 上級者引継ぎ関連 |
| `priority/critical` | 赤 | 全機能 | 即修正必須 |
| `priority/high` | 橙 | 全機能 | 重大問題 |
| `priority/medium` | 黄 | 全機能 | 計画対応 |

---

## 6. スキーマ名の維持方針

API リクエスト/レスポンスの Pydantic スキーマ名は **旧名称のまま維持** する。
（`DigestRequest` → `DigestRequest` のように改名しない。breaking change になるため。）

| スキーマ名 | 所属機能 | 改名計画 |
|:--|:--|:--|
| `EasyModeInput` | Interactive Writer | 維持 |
| `GenerationResponse` | Interactive Writer | 維持 |
| `GachaRequest` | Gacha Pitch | 維持 |
| `GachaResponse` | Gacha Pitch | 維持 |
| `GachaPlan` | Gacha Pitch | 維持 |
| `DigestRequest` | Quick Digest | 維持 |
| `DigestResponse` | Quick Digest | 維持 |
| `PromotionRequest` | Producer Handoff | 維持 |
| `PromotionResponse` | Producer Handoff | 維持 |

サービスクラスのみ改名（`GachaService` → `GachaPitchService`）し、スキーマは外部 API 互換性のために旧名称を維持する。

---

## 7. リビジョン履歴

| 日付 | 版 | 変更内容 |
|:--|:--|:--|
| 2026-09-01 | 1.0.0 | 初版作成 |
