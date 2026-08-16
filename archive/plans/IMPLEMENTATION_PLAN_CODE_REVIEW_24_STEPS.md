# コードレビュー改善 実装計画書（24ステップ版）

**対象レビュー**: `CODE_REVIEW_DETAILED.md`（kaku-hegemony v3.2, 2026-08-14）
**目的**: レビューで指摘された技術的負債（巨大ファイル・循環依存・型安全性・グローバル状態・テスト不備・依存管理）を、**低性能LLMでも1ステップずつ確実に実装できる**よう24の小さなステップに分割。
**方針**: 各ステップは「単一の焦点・単一のPR」で済むよう最小単位に切り分け、必ず既存テスト（`pytest`）と型検査（`mypy`）で検証する。

---

## 進め方の共通ルール（全ステップ共通）

1. 各ステップ開始前に `git status` でクリーンであることを確認する。
2. 変更はそのステップの範囲に**のみ**留める（他ファイルへの波及は次ステップへ回す）。
3. 完了時に必ず以下を実行し、エラーが増えていないことを確認する。
   ```bash
   pytest -q            # 既存テストが通ること
   mypy src/            # 新規エラーが増えないこと
   ```
4. ステップごとにコミットする（`git commit`）。大きなPRは作らない。
5. 完了基準を満たしたら次へ。満たせない場合はそのステップだけで止める。

---

## Phase A: 現状把握・計測基盤（ステップ 1-3）

### Step 1: 改善前のベースライン指標を計測する
**目的**: レビュー KPI（循環依存数・最大ファイル行数・`Any` 使用数・mypy エラー数・テスト結果）の「改善前数値」を記録する。
**対象**: リポジトリ全体
**作業内容**:
- 以下のコマンド出力を `docs/REFACTOR_BASELINE.md` に貼り付ける。
  ```bash
  echo "=== 循環依存 ===" ; (madge --circular src/ 2>/dev/null || echo "madge未導入")
  echo "=== 最大ファイル行数 ===" ; find src -name "*.py" | xargs wc -l | sort -n | tail -5
  echo "=== Any 使用箇所数 ===" ; grep -rn "Any" src/ | wc -l
  echo "=== mypy エラー数 ===" ; mypy src/ 2>&1 | tail -3
  echo "=== テスト結果 ===" ; pytest -q 2>&1 | tail -5
  ```
**完了基準**: `docs/REFACTOR_BASELINE.md` に 5 項目の数値が記録されている。

### Step 2: 指摘事項をチケット化する
**目的**: レビュー指摘を追跡可能なチケットリストにする。
**対象**: `docs/REFACTOR_TICKETS.md`（新規作成）
**作業内容**:
- `CODE_REVIEW_DETAILED.md` の「優先度別改善提案」15 項目（Critical 1-4 / High 5-8 / Medium 9-12 / Low 13-15）を表形式で転記。
- 各項目に「対応ステップ番号」列を追加し、この計画のステップと紐付ける。
**完了基準**: 15 項目すべてがステップ番号と紐付いて `docs/REFACTOR_TICKETS.md` に記載されている。

### Step 3: テストのベースラインを緑にする
**目的**: リファクタ前の「テストが通る状態」を保証する。
**対象**: 既存テスト
**作業内容**:
- `pytest -q` を実行し、失敗がある場合はこの時点では触らず、現状の失敗リストを `docs/REFACTOR_BASELINE.md` に追記する。
- カバレッジ計測環境が未整備なら `.coverage` の存在を確認するだけでよい。
**完了基準**: 現在のテスト成功/失敗状況が文書化されている。

---

## Phase B: グローバル状態のDI一本化（ステップ 4-6）

### Step 4: `get_db_manager()` の呼び出し箇所を洗い出す
**目的**: グローバルDBシングルトン（`_GLOBAL_DB_MANAGER`）への依存箇所を特定する。
**対象**: `src/backend/database/`（および呼び出し元）
**作業内容**:
- `grep -rn "get_db_manager\|_GLOBAL_DB_MANAGER" src/` を実行し、ファイル・行番号リストを `docs/REFACTOR_TICKETS.md` の該当チケットに記録。
**完了基準**: 呼び出し箇所の一覧が記録されている。

### Step 5: 1ファイル目の `get_db_manager()` を DI 経由へ置換する
**目的**: グローバル参照の排除を1箇所ずつ安全に進める（最初の1ファイルのみ）。
**対象**: Step 4 で見つけたリストの「最初の1ファイル」
**作業内容**:
- そのファイル内の `get_db_manager()` 呼び出しを、`AppContainer.db()`（または注入された `repo`/`db`）への参照に置換する。
- 引数追加が必要なら最小限で行う。
**完了基準**: 対象ファイル内に `get_db_manager()` の呼び出しがなく、`pytest -q` が通る。

### Step 6: 残りの `get_db_manager()` を置換しグローバル変数を削除する
**目的**: グローバルシングルトンを完全に廃止し DI 一本化する（チケット 4 完了）。
**対象**: 残りのすべての呼び出しファイル
**作業内容**:
- Step 5 と同じ置換を残り全部に適用。
- `_GLOBAL_DB_MANAGER` 変数とフォールバック分岐を削除し、`get_db_manager()` を「DI コンテナから取得する薄いラッパ」のみにする（呼び出し側が完全移行したら関数ごと削除）。
**完了基準**: `grep -rn "_GLOBAL_DB_MANAGER" src/` が 0 件。`mypy src/` エラー増加なし。

---

## Phase C: 循環依存の解消（ステップ 7-9）

### Step 7: `engine.py` の `_legacy_dep` パターンを洗い出す
**目的**: ランタイム解決されている循環依存箇所を特定する。
**対象**: `src/backend/engine.py`
**作業内容**:
- `grep -rn "_legacy_dep" src/` を実行し、依存元→依存先の関係を `docs/REFACTOR_TICKETS.md` に図式化して記録。
**完了基準**: 循環依存の経路（engine → agents → backend）がリスト化されている。

### Step 8: 後方互換エイリアス `AppContainer = InfraContainer` を整理する
**目的**: 意図的なエイリアスが原因の import 循環を減らす。
**対象**: `src/core/container/`
**作業内容**:
- エイリアスを使っている呼び出し元を `InfraContainer` / `AppContainer2` の本来の名前に統一する（影響が小さいものから1ファイルずつ）。
- エイリアス定義側には「廃止予定」コメントを残す（このステップでは削除しない）。
**完了基準**: 新規のエイリアス利用が増えておらず、`pytest -q` が通る。

### Step 9: 循環依存ゼロを確認・記録する
**目的**: Phase C 完了の検証（チケット 3 完了）。
**対象**: リポジトリ全体
**作業内容**:
- `madge --circular src/` を実行（未導入なら `pip install madge` はせず、手動で Step 7 の経路が消えたことを確認）。
- 循環が残る場合はこのステップで明示的に残件を `docs/REFACTOR_TICKETS.md` に記録し、次ステップへ進まない。
**完了基準**: 循環依存が 0（または既知の残件のみでリスト化済み）。

---

## Phase D: `writing.py` の分割（ステップ 10-14）

> レビュー最大の問題（2,425行・God class）。5つの責務を別クラスへ順次抽出する。

### Step 10: `ContextBuilder` を抽出する（文脈構築 ~300行）
**目的**: `build_full_writing_context` を独立クラスへ分離（チケット 1 の一部）。
**対象**: `src/agents/writing.py`
**作業内容**:
- 同じディレクトリに `context_builder.py` を新規作成し、`ContextBuilder` クラスを定義。
- `build_full_writing_context` のロジックをそのままメソッドとして移動。
- `WritingAgent` 側は `ContextBuilder(self).build_full_writing_context(...)` を呼ぶように変更（動作変更なし）。
**完了基準**: `writing.py` の該当メソッドが削除され、`pytest -q` が通る。

### Step 11: `PromptComposer` + `EroticEnhancer` を抽出する（~400行）
**目的**: プロンプト構築・官能処理を分離（チケット 1 の一部）。
**対象**: `src/agents/writing.py`
**作業内容**:
- `prompt_composer.py` と `erotic_enhancer.py` を新規作成。
- `write_episode` 内の「プロンプト組み立て」と「官能強化」のブロックをそれぞれへ移動。
- 元クラスは委譲呼び出しのみにする。
**完了基準**: 該当ロジックが移動し、`pytest -q` が通る。

### Step 12: `EpisodePipeline` を抽出する（~500行）
**目的**: エピソード生成パイプラインを分離（チケット 1 の一部）。
**対象**: `src/agents/writing.py`
**作業内容**:
- `episode_pipeline.py` を新規作成し、エピソード生成の一連フローを移動。
- `WritingAgent` は `EpisodePipeline(...).run()` を呼ぶ形にする。
**完了基準**: パイプライン処理が移動し、`pytest -q` が通る。

### Step 13: `SchedulerCoordinator` を抽出する（~200行）
**目的**: ストリーミングスケジューラ連携を分離（チケット 1 の一部）。
**対象**: `src/agents/writing.py`
**作業内容**:
- `scheduler_coordinator.py` を新規作成し、スケジューラ操作ブロックを移動。
- `WritingAgent` は委譲する。
**完了基準**: スケジューラ連携が移動し、`pytest -q` が通る。

### Step 14: `writing.py` の統合確認・不要コード削除（チケット 1 完了）
**目的**: 分割後の整合性を確認し、古い動的プロパティ（`pm` 等）を整理する。
**対象**: `src/agents/writing.py`
**作業内容**:
- 移動漏れがないか確認し、空になったメソッド・重複を削除。
- `pm` プロパティ等の「別名エイリアス」を本名（`prompt_manager`）へ統一。
- `wc -l src/agents/writing.py` が 500 行未満になったことを記録。
**完了基準**: `writing.py` が 500 行未満、`pytest -q` が通る。

---

## Phase E: `erotic_integrity.py` の分割（ステップ 15-17）

> レビュー最凶の巨大ファイル（99,091行）。機能別モジュールへ分割する。

### Step 15: `erotic/vocabulary.py` を抽出する
**目的**: 語彙バンク機能を独立モジュールへ（チケット 2 の一部）。
**対象**: `src/agents/erotic_integrity.py`
**作業内容**:
- `src/agents/erotic/vocabulary.py` を新規作成（ディレクトリも新規）。
- 語彙バンク関連の定数・関数を移動。
- 元ファイルは `from .erotic.vocabulary import *` 相当の再エクスポートで後方互換を保つ。
**完了基準**: 語彙機能が移動し、`pytest -q` が通る（元ファイルの import は壊さない）。

### Step 16: `erotic/curve.py` を抽出する
**目的**: カーブ生成機能を分離（チケット 2 の一部）。
**対象**: `src/agents/erotic_integrity.py`
**作業内容**:
- `src/agents/erotic/curve.py` を新規作成し、カーブ生成ロジックを移動。
- 元ファイルは再エクスポートで互換維持。
**完了基準**: カーブ機能が移動し、`pytest -q` が通る。

### Step 17: `erotic/evaluator.py` + `erotic/filter.py` を抽出し、元ファイルを薄い集約へ（チケット 2 完了）
**目的**: 評価器・フィルタを分離し、巨大ファイルを「再エクスポートのみ」にする。
**対象**: `src/agents/erotic_integrity.py`
**作業内容**:
- `src/agents/erotic/evaluator.py` と `src/agents/erotic/filter.py` を作成し、該当ロジックを移動。
- `erotic_integrity.py` を「各サブモジュールから再エクスポートするだけのファイル」に削減。
- `wc -l src/agents/erotic_integrity.py` が 500 行未満になったことを記録。
**完了基準**: `erotic_integrity.py` が 500 行未満、`pytest -q` が通る。

---

## Phase F: LLM ゲートウェイの分割（ステップ 18-19）

### Step 18: `GeminiClient` / `OpenAIClient` を抽出する
**目的**: `generate_json` の巨大関数をクライアントクラスへ分割（チケット 6 の一部）。
**対象**: `src/core/llm_gateway.py`
**作業内容**:
- `gemini_client.py` と `openai_client.py` を新規作成。
- 各プロバイダ固有の実行ロジック（`_execute_with_stream` / `_execute_without_stream`）を移動。
- `generate_json` は各クライアントへ委譲する形にする（動作変更なし）。
**完了基準**: クライアント分割が完了し、`pytest -q` が通る。

### Step 19: `SchemaValidator` を抽出し `LLMGenerateResultProxy` を実装/削除する（チケット 6 完了）
**目的**: スキーマ検証を分離し、プレースホルダ実装を排除する。
**対象**: `src/core/llm_gateway.py`
**作業内容**:
- `schema_validator.py` を新規作成し、`_validate_response` / フォールバック判定を移動。
- `LLMGenerateResultProxy.generate()` の `return {}, "", None` プレースホルダを、実際の検証・変換ロジックへ置き換えるか、未使用ならクラスごと削除する。
- `OpenAIApiClient` の毎回生成していた `AsyncOpenAI` クライアントをインスタンス化時に1回だけ生成するよう修正。
**完了基準**: プレースホルダがなくなり、`mypy src/` エラー増加なし、`pytest -q` が通る。

---

## Phase G: リトライデコレータのクラス化（ステップ 20）

### Step 20: `RetryPolicy` クラスへリファクタしヘルパをメソッド化する（チケット 5 完了）
**目的**: 400行超のデコレータをクラスベース・SRP準拠にする。
**対象**: `src/services/retry_decorator.py`
**作業内容**:
- 散在するロック操作（`_increment_active` / `_decrement_active`）をメソッド化。
- デコレータ本体を `RetryPolicy` クラスのメソッドへ移動（動作は変えない）。
- `reporter` への直接依存を `IReporter` Protocol 経由にする。
**完了基準**: クラス化が完了し、`mypy src/` エラー増加なし、`pytest -q` が通る。

---

## Phase H: 型安全性・設定一元化（ステップ 21-22）

### Step 21: `writing.py` 等の `Any` を Protocol/具象型へ置換する（小さく・チケット 7 の一部）
**目的**: 代表的な `Any` 使用を減らす（一気に全部はしない）。
**対象**: `src/agents/writing.py` の `repo: Any` / `style_rag: Any` / `plot_expander: Any`
**作業内容**:
- 各フィールドについて、既存の Protocol（`IRepository` 等）または具象型を import し、型注釈を置換。
- 置換できないものは `# type: ignore` ではなく `# TODO: 型特定が必要` コメントに留める（このステップでは1ファイル・数箇所のみ）。
**完了基準**: `grep -n "Any" src/agents/writing.py` の該当行が減り、`mypy src/agents/writing.py` が改善。

### Step 22: `ConfigManager` 単一エントリポイントを作成する（チケット 8 完了）
**目的**: 散在する設定（`constants.py` / `models.py` / `project_context.py` / `settings.py`）を一元化する。
**対象**: `config/`
**作業内容**:
- `config/manager.py` に `ConfigManager` クラスを新規作成し、既存の4ファイルから値を集約するプロパティを追加。
- 既存コードはまだ移行しない（このステップは「単一エントリポイントの作成」のみ）。
- `get_config()` が `ConfigManager` を返すよう最小修正。
**完了基準**: `ConfigManager` が作成され、`pytest -q` が通る。

---

## Phase I: テスト・依存・監視（ステップ 23-24）

### Step 23: テストインフラ整備（カバレッジ計測・モック統一）（チケット 9 の一部）
**目的**: カバレッジ計測環境を整備し、重複モックを1つにまとめる。
**対象**: `tests/`、`pytest.ini`
**作業内容**:
- `pytest.ini` に `--cov=src --cov-report=term-missing` を追加（または `pyproject.toml` の `[tool.pytest.ini_options]` に記載）。
- `tests/mocks/` の複数 `mock_llm.py` を確認し、共通1つへ統合する（影響が小さいものから）。
**完了基準**: `pytest` 実行時にカバレッジが表示される。

### Step 24: 依存関係のバージョン固定（チケット 14 完了）
**目的**: サプライチェーン攻撃リスクを減らす。
**対象**: `requirements.txt`
**作業内容**:
- `requirements.txt` の未固定パッケージ（`google-genai`, `httpx`, `huey`, `redis` 等）に、現在インストールされているバージョンを `==` で固定。
  - 固定バージョンは `pip show <pkg> | grep Version` で取得。
- `pyproject.toml` の `[project]` に `dependencies` が未記載なら、requirements と同期する方針を `docs/REFACTOR_TICKETS.md` にメモ。
**完了基準**: `requirements.txt` の主要パッケージがバージョン固定され、`pip install -r requirements.txt` がエラーなく解析される。

---

## 完了後の確認（全ステップ終了時）

- `docs/REFACTOR_BASELINE.md`（Step 1）と最終状態を比較し、KPI の改善を記録：
  - 循環依存数: ~15 → 目標 0
  - 最大ファイル行数: 99,091 → 目標 < 500
  - `Any` 使用箇所: 200+ → 目標 < 20（Step 21 は一部なので段階的）
  - テストカバレッジ: 不明 → 目標 > 80%
  - mypy エラー数: 50+ → 目標 0（段階的）
- `docs/REFACTOR_TICKETS.md` の全チケットを「完了 / 残件」で更新。

---

## ステップ → レビューチケット 対応表

| ステップ | レビューチケット | 優先度 |
|----------|------------------|--------|
| 1-3 | （計測・基盤） | - |
| 4-6 | 4. グローバルDBシングルトン廃止 | Critical |
| 7-9 | 3. 循環依存解消 | Critical |
| 10-14 | 1. writing.py 分割 | Critical |
| 15-17 | 2. erotic_integrity.py 分割 | Critical |
| 18-19 | 6. LLMゲートウェイ分割 | High |
| 20 | 5. リトライデコレータ クラス化 | High |
| 21 | 7. 型ヒント Any 排除（一部） | High |
| 22 | 8. 設定一元化 | High |
| 23 | 9. テストインフラ整備（一部） | Medium |
| 24 | 14. 依存関係バージョン固定 | Low |
