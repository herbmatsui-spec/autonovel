# リファクタリング実装計画書（48ステップ）

本計画は実装を行わず、指摘された5つの改善余地について **48の小さなステップ** に分割した作業計画である。各ステップは独立してレビュー・検証可能な粒度とし、各ステップの冒頭に影響度（高/中/低）と対象領域を明記する。

---

## 0. 共通前提・ガイドライン

- 1ステップ=1コミットを原則とする。
- 各ステップ完了後、該当領域のテスト（`pytest tests/` および対象ユニットテスト）が GREEN であることを確認する。
- 削除は原則として「論理削除→CIで非参照確認→物理削除」の2段階で行う。
- 互換性が必要な公開APIは `DeprecationWarning` を経て削除する。

---

## A. DI コンテナの循環参照リスク（影響度：中）

> 課題: [`src/core/container.py`](src/core/container.py:338) において `lambda *a, **kw: AppContainer.llm().generate_json(...)` 形式の遅延参照が多用されており、初期化順序に暗黙依存が存在する。

### Step 1 【中/DI】遅延参照の現状把握と依存グラフの作成
- [`container.py`](src/core/container.py:338) の `lambda`参照をすべて抽出し、`AppContainer.<llm|repo|pm|ctx_mgr|...>()` の依存先を一覧化した `plans/di_dependency_map.md` を作成する。

### Step 2 【中/DI】循環参照の有無を起動時テストで検出
- `tests/perf_container_test.py` に「全プロバイダ(get_all_providers)を解決し、例外なくインスタンス化できるか」を検証するスモークテストを追加する（まだ lambda 含む現状でのベースライン）。

### Step 3 【中/DI】`LazyProvider` ヘルパークラスの設計
- [`container.py`](src/core/container.py:86) の `FactoryProvider` に並列して、`AppContainer.<x>` を安全に遅延解決する `LazyProvider` クラスを設計（docstring/型シグネチャのみ。実装は次ステップ）。

### Step 4 【中/DI】`LazyProvider` の最小実装
- `LazyProvider` を実装し、`__call__` で `AppContainer.<provider>()` を呼び出す。任意の `method_name` を渡して部分適用できるよう `generate_json` 等のメソッド束縛に対応する。

### Step 5 【中/DI】`LazyProvider` のユニットテスト追加
- 遅延解決のタイミング・例外伝播・override 時の挙動を検証するユニットテストを `tests/` に追加する。

### Step 6 【中/DI】`auditor` プロバイダの lambda → LazyProvider 置換
- [`auditor`](src/core/container.py:338) の `generate_json=lambda...` を `LazyProvider(AppContainer.llm, method="generate_json")` に置換。テスト GREEN を確認。

### Step 7 【中/DI】`marketing` プロバイダの置換
- [`marketing`](src/core/container.py:339) を `LazyProvider` 化。

### Step 8 【中/DI】`planner.generate_json` の置換
- [`planner`](src/core/container.py:355) の lambda を置換。

### Step 9 【中/DI】`validator` プロバイダの置換
- [`validator`](src/core/container.py:363) を `LazyProvider` 化。

### Step 10 【中/DI】`narrative.generate_json` の置換
- [`narrative`](src/core/container.py:366) を `LazyProvider` 化。

### Step 11 【中/DI】`critique` プロバイダの置換
- [`critique`](src/core/container.py:373) を `LazyProvider` 化。

### Step 12 【中/DI】残存 lambda の一括 scan と最終確認
- `grep` で `lambda \*a` を再検索し、残存0を確認。Step 2 のスモークテストを再実行。

### Step 13 【中/DI】初期化順序の明文化
- `container.py` の各 Provider 定義に「依存するProvider」行をコメントで明記し、順序依存を可視化。

### Step 14 【中/DI】DI 整備の完了確認とドキュメント化
- `docs/di_architecture.md` に LazyProvider の利用規約と循環参照禁止ルールを記載。

---

## B. レガシー・移行コードの共存（影響度：高／保守性）

> 課題: [`archive/`](archive/legacy_scripts/) 配下の大量スクリプト、[`engine.py`](src/backend/engine.py:47)（ファサード109行で停止）と [`engine_narrative.py`](src/backend/engine_narrative.py:61) 等の分割モジュールが混在。

### Step 15 【高/レガシー】`archive/` の覧別と依存スキャン
- `archive/legacy_scripts/`, `archive/scratch/` 内のファイル一覧と、`src/` からの import 有無を grep で確認し、`plans/archive_inventory.md` に整理。

### Step 16 【高/レガシー】archive 配下のテストカバレッジ確認
- archive 配下が `tests/` から参照されていないことを確認。参照がある場合は別途退避計画に記録。

### Step 17 【高/レガシー】archive/legacy_scripts/ の①分離
- 参照なしを確認の上、`archive/legacy_scripts/` を `archive/_deprecated/legacy_scripts_2025Q2/` にディレクトリ移動（git mv）。

### Step 18 【高/レガシー】archive/scratch/ の分離
- 同様に `archive/scratch/` を `archive/_deprecated/scratch_2025Q2/` に移動。

### Step 19 【高/レガシー】engine.py ファサード現状分析
- [`engine.py`](src/backend/engine.py:47) の残存メソッド一覧（[`sync_bible`](src/backend/engine.py:99), [`resolve_bible_setting`](src/backend/engine.py:105) 等）を抽出し、呼び出し元（[`src/backend/server.py`](src/backend/server.py:216), `streamlit_app/`, `tests/`）を grep。

### Step 20 【高/レガシー】engine.py 呼び出し元の縮小計画策定
- 各呼び出し元を `engine.writer`/`engine.repo` 直接参照へ切替する移行リストを `plans/engine_migration_list.md` に作成。

### Step 21 【高/レガシー】server.py 側の engine ファサード参照の置換
- [`server.py`](src/backend/server.py:216) の `engine.xxx()` を `engine.<sub_component>().xxx()` に書き換え（1メソッド単位）。テスト実行。

### Step 22 【高/レガシー】streamlit_app/ 側の参照置換
- `streamlit_app/` 配下の `engine.xxx` を同様に置換。

### Step 23 【高/レガシー】tests/ 配下の参照置換
- `tests/` から `engine.xxx()` を呼ぶ箇所を置換。モック調整含む。

### Step 24 【高/レガシー】engine.py の委譲メソッド削除（sync_bible/resolve_bible_setting）
- [`engine.py`](src/backend/engine.py:99) の2メソッドを削除し、呼び出し元を `engine.bible_agent` / `engine.repo` に寄せる。

### Step 25 【高/レガシー】engine.py の `_is_light_style` 移動
- [`engine.py`](src/backend/engine.py:89) の `_is_light_style` は [`engine_utils.is_light_style`](src/backend/engine_utils.py:16) と重複。engine から削除して utils 経由に統一。

### Step 26 【高/レガシー】engine_narrative.py / engine_context.py 等 分割モジュールの境界確認
- 各 `engine_*.py` の責務表を `docs/engine_module_boundaries.md` に整理し、import の向きが engine.py → engine_*.py の一方向であることを確認。

### Step 27 【高/レガシー】engine.py を薄ファサードに削減
- 最終的にコンテナ取得のみを行う `UltimateHegemonyEngine.__init__` + 各サブコンポーネント公開プロパティのみの構成に削減（<60行目標）。

### Step 28 【高/レガシー】dead-code 除去の lint/CI 仕組み
- `mypy --no-implicit-reexports` / `ruff` で unused import を検出する CI ステップを追加検討（設定ファイルのみ作成）。

---

## C. 重複メソッド（影響度：中）

> 課題: [`planning.py`](src/agents/planning.py:145) に `extract_and_sync_foreshadowing` が 2回定義（145-203, 205-262）。

### Step 29 【中/重複】両定義の差分比較
- 145-203 と 205-262 の実装差分を `plans/planning_dup_diff.md` に記録。実際に Python が後者を採用していることを確認。

### Step 30 【中/重複】参照元（呼び出し元）の洗い出し
- `extract_and_sync_foreshadowing` の外部呼び出し元を grep で特定し、後者定義の振る舞いに依存しているか確認。

### Step 31 【中/重複】後者（205-262）実装を正とし前者を論理削除
- 145-203 を削除し、205-262 を本来の位置（145以降）に統合して1つにする。

### Step 32 【中/重復】リネーム/スロット整理（必要時）
- 余分なローカルクラス定義（`ForeshadowingExtract` 等）が二重定義で残らないよう、1箇所に集約。

### Step 33 【中/重複】重複検出の CI ルール追加
- `ruff --select F811`（関数再定義）を CI/`pyproject.toml` に追加し、今後の重複定義を検出。

### Step 34 【中/重複】planning.py の回帰テスト追加
- `extract_and_sync_foreshadowing` の配置/回収両パターンを網羅するユニットテストを `tests/` に追加。

---

## D. 同期/非同期の混在（影響度：中）

> 課題: [`DatabaseManager`](src/backend/database/core.py:95) に非同期メソッドとレガシー同期メソッドが共存。[`DatabaseConnectionWrapper`](src/backend/database/core.py:74) で `__getattr__`/`__setattr__` の動的委譲で型安全性が損なわれている。

### Step 35 【中/DB】DatabaseManager の公開メソッド一覧化
- [`core.py`](src/backend/database/core.py:176) の `enqueue_write`, `execute`, `fetch_one`, `fetch_all`, `fetch_lastrowid` 等の利用状況（同期/非同期/レガシー）を `plans/db_methods_inventory.md` に整理。

### Step 36 【中/DB】`enqueue_write` の呼び出し元特定
- [`enqueue_write`](src/backend/database/core.py:176) に `warnings.warn("enqueue_write is deprecated", DeprecationWarning)` を仕込み、テスト/CI で出力元を把握。

### Step 37 【中/DB】`enqueue_write` 呼び出し元の非同期API移行
- 該当箇所を `execute` (非同期) に置換。1ファイルごとにコミット。

### Step 38 【中/DB】`enqueue_write` の実装を DeprecationWarning 専用に縮小
- 本体を `DeprecationWarning` + 内部で `await self.execute(...)` に縮小し、最終削除を見据える。

### Step 39 【中/DB】`DatabaseConnectionWrapper` の責務再定義
- [`core.py`](src/backend/database/core.py:74) の動的委譲を明示メソッドに置換するための protocol/abstract を `src/backend/database/connection_protocol.py` として設計。

### Step 40 【中/DB】Wrapper の `__getattr__`/`__setattr__` を明示的 property 化
- 頻用の属性（`cursor`, `rowcount` 等）は明示プロパティにし、動的 `__getattr__` は最後にフォールバックのみ残す。

### Step 41 【中/DB】Wrapper の型チェック用 Protocol を定義
- `typing.Protocol` を定義し、mypy が `__getattr__` 依存の暗黙アクセスを指摘できるよう `pyproject.toml` に mypy 設定を追加。

### Step 42 【中/DB】非同期/同期混在の compat メソッドに `async def`/`def` を型注釈で明記
- レガシー同期メソッドには明示的に `def` と `# sync-compat` コメントを付与し、mypy の `async` 混在を警告。

---

## E. 設定管理の分散（影響度：低）

> 課題: [`config/`](config/__init__.py) 配下 JSON/YAML、環境変数、[`config/base.py`](config/base.py:30) の Python 定数、[`ProjectContext`](config/project_context.py:65) 等の取得経路が複数存在。

### Step 43 【低/設定】設定取得経路の現状一覧化
- [`config/base.py`](config/base.py:30)、[`config/models.py`](config/models.py)、[`config/settings.toml`](config/settings.toml)、[`config/project_context.py`](config/project_context.py:65)、環境変数、各 `*.yaml`/`data/*.json` を `plans/config_sources_map.md` に整理。

### Step 44 【低/設定】`ProjectContext.get_setting` の経路一元化方針策定
- 全モジュールが `ProjectContext.get_setting(key)` のみを呼ぶ原則を `docs/config_policy.md` に明文化。

### Step 45 【低/設定】直接 import している `config/base.py` 定数の上書きラッパ追加
- `ProjectContext` に `BASE_DIR`, `DATABASE_URL` 等の遅延プロパティを生やし、`config.base` の直接 import を段階的に置き換えられるようにする（互換維持）。

### Step 46 【低/設定】環境変数の取得を `ProjectContext._env()` 経由に統一
- `os.environ.get(...)` の直接呼び出し箇所を grep で抽出し、`ProjectContext` 経由に順置換。

### Step 47 【低/設定】YAML/JSON 設定読込を `config/data_loader.py` に集約
- [`config/data_loader.py`](config/data_loader.py) を経て `ProjectContext` が参照する形にし、各所の `json.load`/`yaml.safe_load` を整理。

### Step 48 【低/設定】設定不正時の早期失敗と validator 強化
- [`config/validator.py`](config/validator.py:19) の `ConfigValidator` を起動時実行し、設定キーの欠落/重複を CI で検出するスクリプトを `scripts/validate_config.py` として整備（実行設定に追加）。

---

## 完了基準

- 5領域すべての Step が完了し、各 Step のテストが GREEN。
- `archive/_deprecated/` 配下に退避済みの旧スクリプトのみ残存（`src/` からの参照ゼロ）。
- [`engine.py`](src/backend/engine.py:47) が薄ファサード化（<60行）。
- [`planning.py`](src/agents/planning.py:145) の重複解消。
- `DatabaseManager` のレガシー同期メソッドに `DeprecationWarning` 付与 or 削除。
- `ProjectContext` 経由の設定取得が基本経路としてドキュメント化。
