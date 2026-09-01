# Easy Mode Suite（かんたんスイート）

> ジャンル選択や軽い操作だけで小説を生成する **5 つの機能** をまとめた総称。
> 個別の機能名（機能 ID）で会話・タスク・Issue を統一することで、「かんたんモードの何の話か」を 1 単語で示せるようにする。

---

## 1. 全体像

```
Easy Mode Suite
├── Interactive Writer      章単位の対話型自動生成
├── Full Auto Generator     ジャンル指定で完結まで全自動生成
├── Gacha Pitch             3 案ガチャ企画生成
├── Quick Digest            採用案から第1話＋クライマックスを即生成
└── Producer Handoff        上級者モードへの作品引き継ぎ
```

| 機能名 | 想定 UX | エントリポイント | コア実装 | 状態管理 |
|:--|:--|:--|:--|:--|
| **Interactive Writer** | 1 章ずつ書き進める | `POST /easy_mode/generate` | `execute_generation()` | DB + Huey タスク |
| **Full Auto Generator** | ジャンルを選んで放置 | `EasyModeWorkflow.execute()` | `EasyModePipeline` | DB（完了後） |
| **Gacha Pitch** | ガチャで 3 案から選ぶ | `POST /easy_mode/gacha` | `GachaService` | ⚠ プロセスメモリ |
| **Quick Digest** | 第1話＋クライマックスを即読む | `POST /easy_mode/digest` | `DigestService` | ⚠ プロセスメモリ |
| **Producer Handoff** | 上級者モードへ作品を渡す | `POST /easy_mode/promote` | `PromotionService` | ⚠ プロセスメモリ |

⚠ 印の 3 機能は現在プロセスメモリ（`_BOOK_STORE` / `_GACHA_CACHE`）で状態を保持しており、コードレビューで critical 判定を受けている。永続化は別タスクで対応予定。

---

## 2. 機能詳細

### 2.1 Interactive Writer（対話型ライター）

**目的**: ユーザーが現在の章とキャラクター設定を送ると、LLM が次章を執筆して返す。

**API**:

```http
POST /easy_mode/generate
Content-Type: application/json

{
  "chapter_history": ["第1章...", "第2章..."],
  "current_chapter": "第3章の冒頭...",
  "character_params": {
    "name": "主人公",
    "personality": "正義感が強い",
    "ability": "剣術・魔導",
    "genre": "ハイファンタジー (R15)"
  },
  "content_length_limit": 2000
}
```

**フロー**:

```
[Router] generate_content (src/backend/routers/easy_mode.py:118)
  ├─ process_chapter() で本文を切り詰め (1500 文字)
  ├─ BookRepository.create_task() で DB にタスク行を作成
  ├─ huey.enqueue(generate_chapter_task) でタスク投入
  └─ task_id を即時返却

[Huey Worker] execute_generation
  ├─ rag_service.build_rag_context() で GraphRAG/Vector の過去 context を取得
  ├─ NOVEL_USER_PROMPT_WITH_GRAPHRAG_TEMPLATE でプロンプト構築
  ├─ LLMAdapter.generate_text() で本文生成 (max_tokens=2000)
  ├─ graph_pipeline_service.process_chapter_knowledge() でナレッジグラフ更新
  └─ SUGGESTIONS_PROMPT で次話候補を 3 件生成

[ポーリング] GET /easy_mode/status/{task_id}
```

**状態確認**:

```http
GET /easy_mode/status/{task_id}
→ { "status": "pending" | "completed" | "failed", "result": {...} }
```

**エクスポート**:

```http
GET /easy_mode/export/{book_id}
→ ZIP ダウンロード (マーケティング成果物 + 本文 + 設定)
```

---

### 2.2 Full Auto Generator（全自動ジェネレーター）

**目的**: ジャンルを選びだけで、企画 → 設定書 → プロット → 全話執筆 → 完結処理を完了させる。

**エントリ**: `EasyModeWorkflow.execute()` (`src/backend/workflows/easy_mode_workflow.py:20`)

**パラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|:--|:--|:--|:--|
| `genre` | `str` | `"ファンタジー"` | 対象ジャンル |
| `keywords` | `list[str]` | `[]` | キーワード |
| `protagonist_type` | `str` | `"チート主人公"` | 主人公属性 |
| `target_episodes` | `int` | `10` | 目標話数 |
| `words_per_episode` | `int` | `2000` | 1 話あたり目標文字数 |
| `enable_audit` | `bool` | `True` | 監査を有効化 |
| `max_rewrites` | `int` | `2` | 監査不合格時のリトライ上限 |

**フロー**:

```
EasyModeWorkflow.execute()
  ↓
[Pipeline] EasyModePipeline (src/easy_mode/pipeline.py:66)
  ├─ load_preset(genre) でジャンル別プリセットをロード
  ├─ [bible]    設定書 (Bible) を LLM で生成
  ├─ [plot]     全 target_episodes 話分のプロットを一括生成
  ├─ [writing]  各話を LLM で執筆
  │              ├─ spice_guard で官能要素の品質検査
  │              ├─ 不合格なら max_rewrites 回までリトライ
  │              └─ audit_score が target_audit_score (95.0) を目標に推敲
  ├─ [episode_complete] 1 話完了ごとに progress_callback 発火
  └─ [finalizing] 完結処理・メタデータ生成

[結果] SeriesResult (全話のタイトル・本文・audit_score・word_count 等)
  ↓
[Marketing] MarketingAgent → ZIP エクスポート
```

**進捗コールバック**:

| stage | 表示メッセージ |
|:--|:--|
| `bible` | "Bible生成中" |
| `plot` | "プロット生成中" |
| `writing` | "本文執筆中" |
| `episode_complete` | "話完了" |
| `finalizing` | "完結処理中" |

---

### 2.3 Gacha Pitch（ガチャピッチ）

**目的**: ジャンルとキーワードから、3 種類（王道 / 変化球 / ダーク）の企画案をガチャ形式で生成する。

**API**:

```http
POST /easy_mode/gacha
Content-Type: application/json

{
  "genre": "ハイファンタジー",
  "keywords": ["復讐", "裏切り", "覚醒"],
  "temperature": 0.7
}
```

**レスポンス**:

```json
{
  "request_id": "gacha_abc12345",
  "plans": [
    {
      "plan_id": "plan_xxx001",
      "plan_type": "royal",
      "title": "王の帰還",
      "logline": "...",
      "protagonist_summary": "...",
      "charm_point": "..."
    },
    { "plan_type": "curveball", "...": "..." },
    { "plan_type": "dark", "...": "..." }
  ]
}
```

**plan_type の意味**:

| 値 | 意味 | 方向性 |
|:--|:--|:--|
| `royal` | 王道展開 | 読者の期待に 100% 応える爽快な展開 |
| `curveball` | 変化球展開 | 予想外のギャップや設定で魅せる奇抜な展開 |
| `dark` | ダーク展開 | シリアスで深みのある重厚な展開 |

**注意点**:

- 3 案は並列生成され、全体タイムアウトは **30 秒**（`asyncio.wait_for`）
- 各案は最大 2 回まで LLM リトライし、失敗時は固定フォールバック文案を返す
- 結果は `_GACHA_CACHE[request_id]` に保存される（⚠ プロセスメモリ）

---

### 2.4 Quick Digest（クイックダイジェスト）

**目的**: ガチャで採用した 1 案から、全体あらすじ＋第1話＋クライマックス予告を即座に生成する。

**API**:

```http
POST /easy_mode/digest
Content-Type: application/json

{
  "request_id": "gacha_abc12345",
  "selected_plan_id": "plan_xxx001"
}
```

**レスポンス**:

```json
{
  "book_id": "book_xxxxxxxx",
  "title": "王の帰還",
  "synopsis": "全10話のあらすじ...",
  "episode_1_text": "第1話本文...",
  "climax_preview_text": "クライマックス描写...",
  "status": "completed" | "failed"
}
```

**内部処理**:

1. `_GACHA_CACHE[request_id]` から選択された `plan` を取得
2. 全体あらすじ（300 字程度）を LLM で生成
3. 第1話本文（1000〜1500 字）とクライマックス予告（800 字程度）を **並列** 生成（`asyncio.gather`）
4. 結果を `_BOOK_STORE[book_id]` に保存（⚠ プロセスメモリ）

**ステータス**:

| `status` | 意味 |
|:--|:--|
| `processing` | 生成中（現状未使用） |
| `completed` | 正常完了 |
| `failed` | LLM 例外時（フォールバック文言で継続） |

---

### 2.5 Producer Handoff（プロデューサーハンドオフ）

**目的**: かんたんモードで生成した作品データを、上級者モード（Advanced Mode）に引き継ぐ。

**API**:

```http
POST /easy_mode/promote
Content-Type: application/json

{
  "book_id": "book_xxxxxxxx"
}
```

**レスポンス**:

```json
{
  "success": true,
  "redirect_url": "/advanced/book_xxxxxxxx",
  "state_token": "token_xxxxxxxxxxxx"
}
```

**内部処理**:

1. `_BOOK_STORE[book_id]` から作品データを取得
2. 存在しなければ警告ログを出してデフォルト作品を自動作成
3. `book_data["mode"] = "advanced"` に書き換え
4. `state_token` を発行して `redirect_url` を返却

**注意点**:

- ⚠ コードレビューで **book_id 偽造による偽データ注入** が指摘されている
- ⚠ `_BOOK_STORE` がプロセスメモリのため、複数ワーカー環境では整合性が取れない
- 本実装は暫定で、将来的には `Book` テーブルの `mode` カラム更新に置き換える予定

---

## 3. 用語対応表

コードと機能名（機能 ID）の対応表。コメント・docstring・Issue・PR タイトルではこの表を基準にする。

| 概念 | 機能名 | クラス接頭辞 | ログタグ | タスクタイトル例 |
|:--|:--|:--|:--|:--|
| 逐次章生成 | Interactive Writer | `InteractiveWriter*` | `[interactive-writer]` | `[Interactive Writer] RAG キャッシュにヒットしない時のフォールバック実装` |
| 全自動生成 | Full Auto Generator | `FullAuto*` | `[full-auto]` | `[Full Auto] target_audit_score 未達時のリトライ上限` |
| ガチャ企画 | Gacha Pitch | `GachaPitch*` | `[gacha-pitch]` | `[Gacha Pitch] 3 案 LLM 失敗時の固定フォールバック文案を見直し` |
| プレビュー | Quick Digest | `QuickDigest*` | `[quick-digest]` | `[Quick Digest] _BOOK_STORE を DB 永続化に置換` |
| 上級者引継 | Producer Handoff | `ProducerHandoff*` | `[producer-handoff]` | `[Producer Handoff] book_id 存在確認処理を追加` |

---

## 4. アーキテクチャ図

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend (React/Streamlit)                  │
└────┬──────────────────────────────────────┬──────────────────┘
     │                                      │
     │ POST /easy_mode/generate             │ POST /easy_mode/{gacha,digest,promote}
     │ GET  /easy_mode/status/{id}          │ GET  /easy_mode/export/{book_id}
     │                                      │
     ▼                                      ▼
┌────────────────────────┐         ┌────────────────────────┐
│ Interactive Writer     │         │ Gacha Pitch            │
│ (routers/easy_mode.py) │         │ Quick Digest           │
└─────────┬──────────────┘         │ Producer Handoff       │
          │                        └─────────┬──────────────┘
          ▼                                  ▼
┌────────────────────────┐         ┌────────────────────────┐
│ Huey タスクキュー       │         │ Gacha/Digest/Promotion │
│ (SQLite or Redis)      │         │ Service (in-memory)    │
└─────────┬──────────────┘         └─────────┬──────────────┘
          │                                  │
          └──────────────┬───────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Book / Chapter / Bible / Plot / BackgroundTask (DB)        │
│  + GraphRAG / Vector Store / LLM Adapter (OpenAI/Gemini)    │
└──────────────────────────────────────────────────────────────┘
                         ▲
                         │ EasyModeWorkflow.execute()
┌────────────────────────┴─────────────────────────────────────┐
│  Full Auto Generator                                          │
│  EasyModePipeline (src/easy_mode/pipeline.py)                │
│  Bible → Plot → Writing(×N, with spice_guard) → Finalize    │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 既知の問題と今後のタスク

コードレビュー（2026-09-01）で指摘された主な問題は [CHANGELOG.md](../CHANGELOG.md) と Issue で管理する。Easy Mode Suite に関する主なものは以下。

| 機能 | 重要度 | 内容 |
|:--|:--|:--|
| Gacha Pitch / Quick Digest / Producer Handoff | critical | `_GACHA_CACHE` / `_BOOK_STORE` がプロセスメモリ → 永続化必須 |
| Producer Handoff | critical | 存在しない `book_id` で偽データが自動作成される |
| Quick Digest | high | `asyncio.gather` 例外時、フォールバックも `_BOOK_STORE` に残らない |
| Full Auto Generator | medium | `EasyModePipeline` のキャンセル制御が未実装 |
| Interactive Writer | low | レートリミットが `generate` のみ。`status`/`export` は未保護 |

---

## 6. 関連ドキュメント

- [API リファレンス](./api.md)
- [CHANGELOG](../CHANGELOG.md)
- [README](../README.md)
- [CONTRIBUTING](../CONTRIBUTING.md)
- コードレビュー報告書（2026-09-01、内部メモ）

---

## 7. 改訂履歴

| 日付 | 版 | 変更内容 |
|:--|:--|:--|
| 2026-09-01 | 1.0.0 | 初版作成。5 機能の命名を確定。Interactive Writer / Full Auto Generator / Gacha Pitch / Quick Digest / Producer Handoff |
