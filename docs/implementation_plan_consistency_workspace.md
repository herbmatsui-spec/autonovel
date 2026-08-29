# 実装計画書: 決定論的整合性エンジン & ファイルシステム即メモリ

## 概要
本計画は、前回の提案 3（決定論的整合性エンジン）と提案 7（ファイルシステム即メモリ）を Hegemony Novel Engine に統合する手順を、72 の小ステップに分解したものである。各ステップは 1 つの関数・1 つのファイル・1 つのテストレベルで完結し、低性能 LLM でも逐次実装可能。

**目標工数**: 約 2 週間（1 日 5 ステップ）

**依存ライブラリ（すべて既存 or pip 一発）**:
- `pathlib`（ファイル操作・標準）
- `pydantic`（データ検証・既存）
- `re`（正規表現・標準）
- `python-dateutil`（日付パース・既存の可能性）
- `watchdog`（ファイル監視・`pip install watchdog`）
- `pyyaml`（frontmatter パース・`pip install pyyaml`）

---

## 全体構成

```
src/
├── consistency/                 # 提案 3: 整合性エンジン
│   ├── __init__.py
│   ├── engine.py                # メインエンジン
│   ├── checkers/
│   │   ├── __init__.py
│   │   ├── base.py              # Checker 基底クラス
│   │   ├── foreshadowing.py     # 伏線未回収検出
│   │   ├── timeline.py          # タイムライン矛盾
│   │   ├── character.py         # キャラ設定齟齬
│   │   ├── world.py             # 世界観矛盾
│   │   └── duplicate.py         # 重複チャプター
│   ├── findings.py              # Finding データモデル
│   ├── filters.py               # "intentional" フィルタ
│   └── injector.py              # LLM Guardian プロンプト注入
│
├── filesystem_memory/           # 提案 7: ファイルシステムメモリ
│   ├── __init__.py
│   ├── paths.py                 # パス定義
│   ├── reader.py                # MD 読込
│   ├── writer.py                # MD 書込
│   ├── watcher.py               # ファイル監視
│   ├── sync.py                  # DB ↔ FS 同期
│   ├── auto_update.py           # 章完了時自動更新
│   └── templates/               # MD 雛形
│       ├── SOUL.md.j2
│       ├── WORLD.md.j2
│       ├── CHARACTERS.md.j2
│       ├── OUTLINE.md.j2
│       ├── STORY_SUMMARY.md.j2
│       └── MEMORY.md.j2
│
├── backend/routers/
│   ├── consistency.py           # 整合性チェック API
│   └── workspace.py             # FS メモリ API
│
├── services/
│   └── workspace_service.py     # ビジネスロジック統合
│
└── tests/
    ├── unit/
    │   ├── test_consistency_*.py
    │   └── test_filesystem_*.py
    └── e2e/
        └── test_workspace_flow.spec.ts
```

---

# Phase 1: ファイルシステムメモリ基盤（ステップ 1 〜 24）

## ステップ 1: パス定義モジュール作成
- ファイル: `src/filesystem_memory/paths.py`
- 内容: プロジェクトルート `WORKSPACE_ROOT = Path("./workspaces")` 定義
- サブディレクトリ: `book_{book_id}/branch_{branch_id}/` 配下に `SOUL.md`, `WORLD.md`, `CHARACTERS.md`, `OUTLINE.md`, `STORY_SUMMARY.md`, `memory/MEMORY.md`, `memory/chapters/`
- ヘルパー関数: `get_workspace_path(book_id, branch_id) -> Path`
- ヘルパー関数: `ensure_workspace_dirs(path) -> None`（全ディレクトリ作成）

```python
# 期待コード（10 行程度）
from pathlib import Path
WORKSPACE_ROOT = Path("./workspaces")
def get_workspace_path(book_id: int, branch_id: int = 1) -> Path:
    return WORKSPACE_ROOT / f"book_{book_id}" / f"branch_{branch_id}"
def ensure_workspace_dirs(path: Path) -> None:
    for sub in ["", "memory/chapters"]:
        (path / sub).mkdir(parents=True, exist_ok=True)
```

## ステップ 2: 単体テスト（パス解決）
- ファイル: `tests/unit/test_filesystem_paths.py`
- テスト: `get_workspace_path(1, 1) == Path("./workspaces/book_1/branch_1")`
- テスト: `ensure_workspace_dirs` で全ディレクトリが作成されること
- 実行: `pytest tests/unit/test_filesystem_paths.py -v`

## ステップ 3: テンプレートディレクトリ作成
- ファイル: `src/filesystem_memory/templates/`
- 6 つの Jinja2 雛形ファイル作成
- 各テンプレートは `{{ book_id }}`, `{{ title }}`, `{{ genre }}` などの変数を含む

## ステップ 4: SOUL.md テンプレート作成
- ファイル: `src/filesystem_memory/templates/SOUL.md.j2`
- 内容: AI ペルソナ・文体指針・執筆トーン
- セクション: `# 執筆ペルソナ`, `# 文体ガイド`, `# トーンとリズム`, `# 禁則事項`

## ステップ 5: WORLD.md テンプレート作成
- ファイル: `src/filesystem_memory/templates/WORLD.md.j2`
- 内容: 世界観・地理・歴史・魔法体系
- セクション: `# 概要`, `# 地理`, `# 歴史年表`, `# 種族・組織`, `# 特殊システム`

## ステップ 6: CHARACTERS.md テンプレート作成
- ファイル: `src/filesystem_memory/templates/CHARACTERS.md.j2`
- 内容: 登場人物一人ずつのプロフィール
- セクション: `# 主人公`, `# ヒロイン`, `# サブキャラ`, `# 敵対者`, `# 関係図`

## ステップ 7: OUTLINE.md テンプレート作成
- ファイル: `src/filesystem_memory/templates/OUTLINE.md.j2`
- 内容: 章ごとのプロット概要
- セクション: `# 全体構成`, `# 第 1 章: ...`, `# 第 2 章: ...`

## ステップ 8: STORY_SUMMARY.md テンプレート作成
- ファイル: `src/filesystem_memory/templates/STORY_SUMMARY.md.j2`
- 内容: 物語全体の要約（章要約の集約）
- セクション: `# あらすじ`, `# 現在の章まで`, `# 未回収要素`

## ステップ 9: MEMORY.md テンプレート作成
- ファイル: `src/filesystem_memory/templates/MEMORY.md.j2`
- 内容: グローバル長期記憶
- セクション: `# 重要なプロットイベント`, `# キャラ状態変化`, `# 世界観変更`, `# 読者への伏線`

## ステップ 10: MD 読込モジュール作成
- ファイル: `src/filesystem_memory/reader.py`
- 関数: `read_file(path: Path) -> str`
- 関数: `read_with_frontmatter(path: Path) -> Tuple[dict, str]`（YAML frontmatter + 本文）
- 関数: `list_chapter_summaries(book_id: int) -> List[Path]`

## ステップ 11: 単体テスト（MD 読込）
- ファイル: `tests/unit/test_filesystem_reader.py`
- テスト: 正常な MD 読込
- テスト: 存在しないファイルで `FileNotFoundError`
- テスト: frontmatter 付き MD のパース

## ステップ 12: MD 書込モジュール作成
- ファイル: `src/filesystem_memory/writer.py`
- 関数: `write_file(path: Path, content: str) -> None`
- 関数: `write_with_frontmatter(path: Path, metadata: dict, content: str) -> None`
- 関数: `update_section(path: Path, section_name: str, new_content: str) -> None`（特定セクションだけ置換）

## ステップ 13: 単体テスト（MD 書込）
- ファイル: `tests/unit/test_filesystem_writer.py`
- テスト: ファイル作成・上書き
- テスト: 特定セクション更新（前後保持）

## ステップ 14: プロジェクト初期化 API
- ファイル: `src/backend/routers/workspace.py`
- エンドポイント: `POST /api/workspace/{book_id}/init`
- 処理: 既存 book データからテンプレートを render し、6 つの MD ファイルを一括生成
- レスポンス: 生成されたファイルパスのリスト

## ステップ 15: プロジェクト初期化サービス
- ファイル: `src/services/workspace_service.py`
- 関数: `init_workspace(book_id: int) -> List[Path]`
- 内部: DB から Book, Chapter, Character, Plot を取得 → テンプレ変数に注入

## ステップ 16: ルータ登録
- ファイル: `src/backend/server.py` の `router_modules` に追加
- `"src.backend.routers.workspace"` を挿入

## ステップ 17: ファイル読込 API
- エンドポイント: `GET /api/workspace/{book_id}/files/{filename}` (filename: SOUL|WORLD|CHARACTERS|OUTLINE|STORY_SUMMARY|MEMORY)
- レスポンス: ファイル内容（テキスト）

## ステップ 18: ファイル書込 API
- エンドポイント: `PUT /api/workspace/{book_id}/files/{filename}`
- リクエスト body: `{ "content": "..." }` または `{ "metadata": {...}, "content": "..." }`
- 処理: ファイル上書き + DB の最終更新日時更新

## ステップ 19: 章サマリ一覧 API
- エンドポイント: `GET /api/workspace/{book_id}/memory/chapters`
- レスポンス: `[{ "ep_num": 1, "filename": "chapter_01.md", "summary": "..." }, ...]`

## ステップ 20: 単体テスト（API 統合）
- ファイル: `tests/unit/test_workspace_api.py`
- テスト: init → 6 ファイル生成確認
- テスト: ファイル取得・更新のラウンドトリップ

## ステップ 21: 章サマリ自動生成
- ファイル: `src/filesystem_memory/auto_update.py`
- 関数: `generate_chapter_summary(chapter_content: str) -> str`（LLM 呼び出し）
- 関数: `update_chapter_memory(book_id: int, ep_num: int, summary: str) -> None`
- 内部: `memory/chapters/chapter_{ep_num:02d}.md` を生成

## ステップ 22: 章完了時の自動更新フック
- ファイル: `src/backend/tasks.py` の `execute_service_workflow` 配下
- 章生成完了直後に `update_chapter_memory` を呼び出す
- 失敗しても章生成自体は失敗させない（ログのみ）

## ステップ 23: ファイル監視モジュール作成
- ファイル: `src/filesystem_memory/watcher.py`
- ライブラリ: `watchdog.observers.Observer`
- イベント: `on_modified` → DB 同期キューに追加
- 用途: ユーザーが手動編集した内容を DB に取り込む

## ステップ 24: 単体テスト（ファイル監視）
- ファイル: `tests/unit/test_filesystem_watcher.py`
- テスト: ファイル変更イベントが捕捉されること
- テスト: 監視停止が正常に動作すること

---

# Phase 2: DB ↔ FS 同期レイヤー（ステップ 25 〜 36）

## ステップ 25: 同期方向の決定
- ファイル: `src/filesystem_memory/sync.py`
- 列挙: `SyncDirection.FS_TO_DB`, `SyncDirection.DB_TO_FS`, `SyncDirection.BIDIRECTIONAL`
- デフォルト: FS_TO_DB（手動編集が優先）

## ステップ 26: 同期マッピングテーブル
- ファイル: `src/filesystem_memory/sync.py`
- 辞書: `FILE_TO_MODEL = {"SOUL.md": Style, "WORLD.md": Bible, "CHARACTERS.md": Character, ...}`
- 各エントリに `model_class`, `parse_function`, `serialize_function`

## ステップ 27: SOUL.md → Style DTO パーサ
- 関数: `parse_soul(content: str) -> StyleData`
- 抽出: 「文体」「トーン」「禁則」の各セクション
- 戻り値: Pydantic モデル

## ステップ 28: WORLD.md → Bible パーサ
- 関数: `parse_world(content: str) -> BibleData`
- 抽出: JSON コードブロック（` ```json ` 内に埋め込まれた構造化データ）
- フォールバック: 自由文を `revealed` に格納

## ステップ 29: CHARACTERS.md → Character 一括パーサ
- 関数: `parse_characters(content: str) -> List[CharacterData]`
- 分割: `## 名前` で見出しごとに分割
- 各セクション: `名前`, `役割`, `性格`, `能力`, `関係` を `:` 形式で抽出

## ステップ 30: OUTLINE.md → Plot 一括パーサ
- 関数: `parse_outline(content: str) -> List[PlotData]`
- 抽出: `# 第 N 章: タイトル` 形式

## ステップ 31: シリアライザ（DB → MD）
- 関数: `serialize_soul(style: StyleData) -> str`
- 関数: `serialize_world(bible: BibleData) -> str`
- 関数: `serialize_characters(chars: List[CharacterData]) -> str`
- 関数: `serialize_outline(plots: List[PlotData]) -> str`
- 各関数は Jinja2 テンプレートを使用

## ステップ 32: 単方向同期（FS → DB）
- 関数: `sync_fs_to_db(book_id: int) -> SyncReport`
- 内部: 各 MD ファイルをパーサで読み取り、DB を upsert
- 戻り値: 更新件数・スキップ件数・エラー件数

## ステップ 33: 単方向同期（DB → FS）
- 関数: `sync_db_to_fs(book_id: int) -> SyncReport`
- 内部: DB から最新状態を取得しシリアライザで MD 出力

## ステップ 34: 双方向同期
- 関数: `sync_bidirectional(book_id: int, prefer: SyncDirection) -> SyncReport`
- 内部: FS と DB のタイムスタンプ比較 → 新しい方を採用
- 衝突時: `prefer` で指定された方向を採用

## ステップ 35: 同期 API
- エンドポイント: `POST /api/workspace/{book_id}/sync`
- リクエスト: `{ "direction": "fs_to_db" }`
- レスポンス: 同期レポート JSON

## ステップ 36: 単体テスト（同期レイヤー）
- ファイル: `tests/unit/test_filesystem_sync.py`
- テスト: パーサ・シリアライザのラウンドトリップ
- テスト: 双方向同期の競合解決

---

# Phase 3: 整合性エンジン基盤（ステップ 37 〜 48）

## ステップ 37: Finding データモデル
- ファイル: `src/consistency/findings.py`
- クラス: `Finding`
  - `category: str` (foreshadowing | timeline | character | world | duplicate)
  - `severity: str` (high | medium | low)
  - `description: str`
  - `evidence: List[Evidence]`
  - `suggestion: str`
  - `is_intentional: bool = False`
  - `intentional_reason: Optional[str] = None`

## ステップ 38: Checker 基底クラス
- ファイル: `src/consistency/checkers/base.py`
- 抽象クラス: `Checker`
  - 抽象メソッド: `check(context: CheckContext) -> List[Finding]`
  - プロパティ: `name`, `category`

## ステップ 39: CheckContext データクラス
- ファイル: `src/consistency/engine.py`
- 内容: チェック対象 book_id, branch_id, chapter 範囲
- プロパティ: 必要なデータ（章・プロット・キャラ・バイブル）を遅延ロード

## ステップ 40: 整合性エンジン本体
- ファイル: `src/consistency/engine.py`
- クラス: `ConsistencyEngine`
- コンストラクタ: `__init__(self, checkers: List[Checker])`
- メソッド: `run(context: CheckContext) -> List[Finding]`
- 内部: 全チェッカーを順次実行、結果をマージ

## ステップ 41: Finding フィルタ
- ファイル: `src/consistency/filters.py`
- 関数: `filter_intentional(findings: List[Finding], dismissed_keys: Set[str]) -> List[Finding]`
- ロジック: `is_intentional=True` または `dismissed_keys` に含まれるものは除外

## ステップ 42: dismissed_keys 永続化
- ファイル: `src/consistency/dismissed_store.py`
- バックエンド: JSON ファイル `workspaces/book_{id}/dismissed_findings.json`
- 関数: `add_dismissal(finding_key: str, reason: str) -> None`
- 関数: `get_all_dismissals() -> Dict[str, str]`

## ステップ 43: 単体テスト（Finding & Engine）
- ファイル: `tests/unit/test_consistency_engine.py`
- テスト: Finding 作成
- テスト: チェッカー 1 つだけ実行
- テスト: 複数チェッカーのマージ

## ステップ 44: 整合性チェック API
- ファイル: `src/backend/routers/consistency.py`
- エンドポイント: `POST /api/consistency/{book_id}/check`
- リクエスト: `{ "ep_num": Optional[int], "branch_id": 1 }`
- レスポンス: `{ "findings": [...], "summary": {...} }`

## ステップ 45: 単一却下 API
- エンドポイント: `POST /api/consistency/{book_id}/dismiss`
- リクエスト: `{ "finding_key": "...", "reason": "..." }`
- 処理: `dismissed_store` に追加

## ステップ 46: 単一却下一覧 API
- エンドポイント: `GET /api/consistency/{book_id}/dismissed`

## ステップ 47: ルータ登録
- ファイル: `src/backend/server.py` の `router_modules` に追加
- `"src.backend.routers.consistency"`

## ステップ 48: 単体テスト（API）
- ファイル: `tests/unit/test_consistency_api.py`
- テスト: チェック実行 → 200 応答
- テスト: 未知の book_id で 404
- テスト: 卻下追加 → 一覧に表示

---

# Phase 4: 個別チェッカー実装（ステップ 49 〜 60）

## ステップ 49: 伏線チェッカー
- ファイル: `src/consistency/checkers/foreshadowing.py`
- クラス: `ForeshadowingChecker`
- ロジック:
  1. `foreshadowing` テーブルから `fulfilled=False` のレコード取得
  2. 現在の章以降の本文に `payoff_location` で指定された文字列が含まれるか検索
  3. 含まれない場合 `Finding(severity=high)` を出力
- テスト: フィクスチャで伏線データ作成 → チェック

## ステップ 50: タイムラインチェッカー
- ファイル: `src/consistency/checkers/timeline.py`
- ロジック:
  1. 各章の `created_at` から時系列ソート
  2. 章内本文の日付表現（`YYYY年MM月DD日`, `X 日後` 等）を抽出
  3. 物語内の日付と実作成日の矛盾を検出
- テスト: 矛盾データ作成 → 高 severity で検出

## ステップ 51: キャラ設定チェッカー
- ファイル: `src/consistency/checkers/character.py`
- ロジック:
  1. `Character` テーブルから全キャラ取得
  2. 各章の本文にキャラ名が出現するか確認
  3. キャラの `registry_data`（性格・能力）と章内行動の矛盾を LLM なしでキーワードマッチ
- 例: 「臆病」キャラが「果敢に突撃」している箇所を検出
- テスト: 偽データで検出確認

## ステップ 52: 世界観チェッカー
- ファイル: `src/consistency/checkers/world.py`
- ロジック:
  1. `bible` テーブルの `settings` から禁止用語・必須用語リストを取得
  2. 各章本文を正規表現で検索
  3. 禁止用語が出現したら `severity=high`
- テスト: 禁止語「魔法」設定で「魔術」が出現するケース

## ステップ 53: 重複チャプターチェッカー
- ファイル: `src/consistency/checkers/duplicate.py`
- ロジック:
  1. 連続 2 章の本文を N-gram（5-gram）で比較
  2. Jaccard 類似度が 0.3 を超えたら `severity=medium`
- ライブラリ: 標準 `set` と `itertools.combinations`
- テスト: 同一文を含むテストデータ

## ステップ 54: チェッカーレジストリ
- ファイル: `src/consistency/checkers/__init__.py`
- 関数: `get_default_checkers() -> List[Checker]`
- 戻り値: 上記 5 つのチェッカーのリスト

## ステップ 55: 単体テスト（伏線チェッカー）
- ファイル: `tests/unit/test_foreshadowing_checker.py`

## ステップ 56: 単体テスト（タイムラインチェッカー）
- ファイル: `tests/unit/test_timeline_checker.py`

## ステップ 57: 単体テスト（キャラチェッカー）
- ファイル: `tests/unit/test_character_checker.py`

## ステップ 58: 単体テスト（世界観チェッカー）
- ファイル: `tests/unit/test_world_checker.py`

## ステップ 59: 単体テスト（重複チェッカー）
- ファイル: `tests/unit/test_duplicate_checker.py`

## ステップ 60: 統合テスト（全チェッカー同時実行）
- ファイル: `tests/integration/test_consistency_all.py`
- テスト: 5 チェッカーすべて有効化 → フィクスチャで複数の矛盾を発生 → すべての Finding が返る

---

# Phase 5: LLM Guardian プロンプト注入（ステップ 61 〜 66）

## ステップ 61: Finding → プロンプト変換
- ファイル: `src/consistency/injector.py`
- 関数: `format_findings_for_prompt(findings: List[Finding]) -> str`
- 出力形式:
```
[整合性チェック結果]
以下の潜在的な問題が検出されました。Guardian はこれらを参考に検証してください:

1. [HIGH] 伏線未回収: "魔王の再臨" が第 5 章で設定されましたが、まだ回収されていません。
   証拠: 第 5 章 L120 "我は再びこの地に蘇るであろう"
   提案: 第 12 章までに回収を検討してください。

2. [MED] 重複: 第 7 章と第 8 章の類似度が 35% です。
   ...
```

## ステップ 62: プロンプト注入フック
- ファイル: `src/backend/workflows/nodes/plot_nodes.py` の `consistency_guardian` ノード
- 修正: ノード実行前に整合性チェック → findings をプロンプトに追加
- 既存の LLM 呼び出しに `findings_text` を追加

## ステップ 63: 単体テスト（注入フォーマット）
- ファイル: `tests/unit/test_injector.py`
- テスト: Finding リスト → 期待文字列フォーマット

## ステップ 64: 性能検証
- ファイル: `tests/load/test_consistency_perf.py`
- 100 章規模でチェック実行時間が **5 秒以内** であることを確認
- 閾値超過時は N-gram のサイズを 3 に下げる等の最適化余地

## ステップ 65: キャッシュ機構
- ファイル: `src/consistency/cache.py`
- ロジック: `book_id + chapter_version` をキーにチェック結果をキャッシュ
- DB 変更時にキャッシュ無効化

## ステップ 66: 単体テスト（キャッシュ）
- ファイル: `tests/unit/test_consistency_cache.py`
- テスト: 同一入力で 2 回目以降はキャッシュヒット
- テスト: 章更新でキャッシュ無効化

---

# Phase 6: フロントエンド統合（ステップ 67 〜 72）

## ステップ 67: React フック: 整合性チェック
- ファイル: `frontend/src/hooks/useConsistencyCheck.ts`
- 引数: `bookId`, `epNum?`
- 戻り値: `{ findings, isLoading, error, refetch }`
- 内部: `fetch('/api/consistency/{bookId}/check')` を呼び出し

## ステップ 68: React フック: FS メモリ
- ファイル: `frontend/src/hooks/useWorkspaceFiles.ts`
- 引数: `bookId`
- 戻り値: `{ files, loadFile, saveFile, isLoading }`
- 内部: 6 ファイルの状態管理

## ステップ 69: 整合性チェック結果表示コンポーネント
- ファイル: `frontend/src/components/ConsistencyPanel/ConsistencyPanel.tsx`
- 表示: Finding を severity 別に色分け（高=赤、中=黄、低=青）
- アクション: 各 Finding に「卻下」ボタン
- 却下時: `POST /api/consistency/{bookId}/dismiss`

## ステップ 70: FS メモリファイルエディタコンポーネント
- ファイル: `frontend/src/components/WorkspaceEditor/WorkspaceEditor.tsx`
- UI: タブで 6 ファイル切替、Monaco Editor or シンプルな textarea
- 「保存」ボタン → `PUT /api/workspace/{bookId}/files/{filename}`

## ステップ 71: フロントエンド統合
- ファイル: `frontend/src/components/BookWorkspace.tsx` の StepShell 内にタブ追加
- 「整合性」タブと「ワークスペース」タブを BookTabBar に追加

## ステップ 72: E2E テスト
- ファイル: `tests/e2e/test_workspace_flow.spec.ts`
- シナリオ:
  1. プロジェクト初期化 → 6 ファイル生成確認
  2. WORLD.md 編集 → DB 同期確認
  3. 整合性チェック実行 → Finding 表示確認
  4. Finding 卻下 → 一覧に追加される
  5. 章生成 → 自動的に `memory/chapters/chapter_NN.md` が作成される

---

# 実装順序と依存関係

```
Phase 1 (1-24)  ─┐
                 ├─→ Phase 3 (37-48) ─→ Phase 4 (49-60) ─→ Phase 5 (61-66)
Phase 2 (25-36) ─┘                                                    │
                                                                       ↓
                                                              Phase 6 (67-72)
```

**推奨実装順**:
1. Phase 1 → 2 を並行（FS メモリは比較的独立）
2. Phase 3 → 4 → 5 を順次（整合性エンジンは依存関係が強い）
3. Phase 6（フロントエンド）は最後

**1 日 5 ステップペース**:
- Week 1: Phase 1 完了（24 ステップ）
- Week 2 前半: Phase 2 + Phase 3 着手（〜36 ステップ）
- Week 2 後半: Phase 4 + 5 完了（〜66 ステップ）
- Week 3: Phase 6 + E2E（72 ステップ）

---

# テスト戦略

| レベル | 対象 | ツール | カバレッジ目標 |
|--------|------|--------|----------------|
| 単体 | 各関数・クラス | pytest | 80 % 以上 |
| 統合 | API エンドポイント | pytest + httpx | 主要パスを 100 % |
| 性能 | チェック時間 | pytest-benchmark | 100 章で 5 秒以内 |
| E2E | UI 全体 | Playwright | 5 シナリオ成功 |

---

# リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| LLM ガード連携時にプロンプト肥大 | トークン消費増 | Finding を最大 20 件に制限、超過分は要約 |
| FS 手動編集で DB と乖離 | 整合性破綻 | 起動時に自動双方向同期、衝突はログ |
| チェッカー偽陽性多発 | ユーザー混乱 | severity 低はデフォルト非表示、UI で toggle |
| ファイル監視イベント洪水 | CPU 過剰 | debounce 1 秒、`watchdog` 推奨設定 |
| Markdown 構文揺れ | パーサ失敗 | パーサは「緩く受け取り、厳密に検証」方針 |

---

# 完了基準（DoD）

- [ ] 全 72 ステップ完了
- [ ] 全単体・統合テストが `pytest` で成功
- [ ] E2E テスト 5 シナリオが `playwright test` で成功
- [ ] 性能検証: 100 章チェック < 5 秒
- [ ] ドキュメント更新: `docs/consistency_engine.md`, `docs/workspace_files.md`
- [ ] README に使用方法セクション追加
- [ ] 既存テスト全件回帰なし
- [ ] Linter (`ruff`, `black`) 警告ゼロ

---

# まとめ

本計画は 72 の小ステップに分解されており、各ステップは:
- 1 ファイル追加 or 1 関数追加
- 1 つのテスト追加
- 30 分〜 2 時間の実装時間

に収まる。低性能 LLM でも、1 ステップずつ順を追えば確実に完遂できる粒度となっている。

**最重要ステップ**:
- ステップ 37-48: Finding モデルと API（整合性エンジンの核）
- ステップ 49-53: 5 つのチェッカー実装（実用性の核）
- ステップ 61-62: LLM Guardian 注入（価値の核）
- ステップ 67-71: UI 統合（ユーザー体験の核）

これらを優先的に実装し、Phase 2 と Phase 6 は余裕があれば取り組む方針でも良い。