# 中長期的メンテナンスコスト削減提案（優先順位順）

> 作成日: 2026-06-27
> 対象プロジェクト: 覇権エンジン (Novel Writing AI System)

---

## 優先順位 第1位: 設定モデルの重複排除（最重要）

### 現在の問題
[`config/settings.py`](../config/settings.py:15) と [`config/project_context.py`](../config/project_context.py:43) に **2つの `GlobalConfigModel` クラス**が存在する。
- `settings.py::GlobalConfigModel` — `ModelRegistry` をネスト保持、独自の `load()` メソッド
- `project_context.py::GlobalConfigModel` — 異なるフィールドセット（`enable_*` 系のみ存在）、`from_toml()` メソッド

さらに `get_config()` では `ConfigValidator.validate_all()` 経由で **3つ目のロードパス** が走る。

### リスク
- フィールド追加時に両方のモデルへの反映忘れが頻発する
- 設定の読み取り結果がどのロードパスを通ったかで変わりうる
- バグの温床（例: `project_context.py:154` の代入漏れ `config_dict["plugins"]`）

### 提案
1. **`settings.py` の `GlobalConfigModel` を削除**し、`project_context.py` のモデルに一本化する
2. `ConfigManager`（settings.py:86）と `get_config/set_config`（project_context.py:106）の重複 Singleton パターンを統合する
3. モデルフィールドと設定ファイルのキーを自動マッピングする（現在の30行近い手動コピペを排除）

---

## 優先順位 第2位: Streamlit 依存の設定レイヤーからの分離

### 現在の問題
[`config/project_context.py::GlobalConfig`](../config/project_context.py:203) が `import streamlit as st` および `from streamlit.runtime.scriptrunner import get_script_run_ctx` を直接 import している。

### リスク
- ユニットテストが Streamlit ランタイムなしでは実行不可能
- CLI ツールやバッチ処理から設定を読み込めない
- 循環インポートや `None` チェックの氾濫 (`if get_script_run_ctx() is not None`)

### 提案
1. **Streamlit 依存を分離**し、純粋な設定コア（Pydantic + ファイルIO）と Streamlit アダプター層に分割する
2. `GlobalConfig` の責務を「設定の保持・バリデーション・永続化」に限定し、Streamlit 同期は別クラスに移す
3. インターフェースとして `ConfigPort` プロトコルを定義し、テスト時は `InMemoryConfigAdapter` を使えるようにする

---

## 優先順位 第3位: PROMPT_TEMPLATES インラインテンプレートのファイル分離

### 現在の問題
[`config/project_context.py:353`](../config/project_context.py:353) に **約70行の Jinja2 テンプレート文字列** がハードコードされている。

### リスク
- テンプレート編集が Python ファイルの編集を伴う（非エンジニア編集不可能）
- シンタックスハイライト・Lint が効かない
- `prompts/` ディレクトリに `.j2` ファイルが散在しているのに、なぜかここだけ inline

### 提案
1. インラインテンプレートを `prompts/ai_producer_audit.j2` として切り出し（既存ファイルがあるが内容が異なる）
2. **重複排除**: 同名ファイル `prompts/ai_producer_audit`（拡張子なし）も存在しており整理が必要
3. `config/__init__.py` からの `PROMPT_TEMPLATES` エクスポートを削除し、`PromptRegistry` 経由のみで提供

---

## 優先順位 第4位: パッケージ __init__.py の名前衝突解消

### 現在の問題
[`config/__init__.py`](../config/__init__.py:13) で以下のようにエクスポートしている：
```python
from .project_context import ProjectContext, GlobalConfig, GlobalConfigModel, set_config, get_config, PROMPT_TEMPLATES
```
しかし `settings.py` の `GlobalConfigModel` を一度 import した後に上書きしており、モジュール状態が不安定。

### リスク
- import 順によって利用可能なクラスが変わる
- 型チェッカー（mypy, pyright）が混乱する
- IDE の補完が正しく動作しない

### 提案
1. `__init__.py` での再エクスポートを整理し、一貫した公開 API サーフェスを定義する
2. 公開するクラスの一覧を `__all__` で明示する
3. 内部モジュール間の import は直接パス指定する（`from config.settings import ...`）

---

## 優先順位 第5位: 設定バリデーションパイプラインの統一

### 現在の問題
設定読み込みに以下の3つの異なるパスが存在する：
1. [`config/settings.py::GlobalConfigModel.load()`](../config/settings.py:50) — TOML + YAML
2. [`config/project_context.py::get_config()`](../config/project_context.py:106) — `ConfigValidator.validate_all()` → 7種類のファイルをロード、しかも lazy
3. [`config/validator.py::ConfigValidator.validate_all()`](../config/validator.py:95) — 全ファイルの独立バリデーション

### リスク
- バリデーションエラー時の動作がパスごとに異なる
- ファイル追加時に3箇所の修正が必要
- 現在の `get_config()` は `SystemExit` を送出してプロセスを強制終了する

### 提案
1. 設定読込を **1つのパイプライン** に統合する（`ConfigLoader.load_all() → validator → singleton`）
2. バリデーションエラー時のポリシーを明確にする（フォールバック / 警告 / 停止）
3. 設定スキーマ定義を一元化し、設定ファイル追加時のコストを下げる

---

## 優先順位 第6位: 重複する設定定数と設定ファイルの統合

### 現在の問題
同じモデル名が以下の4箇所で重複定義されている：
1. [`config/base.py:19-25`](../config/base.py:19) — 定数
2. [`config/settings.toml:2-7`](../config/settings.toml:2) — TOML
3. [`config/models.yaml:2-7`](../config/models.yaml:2) — YAML
4. [`config/settings.py:17-23`](../config/settings.py:17) — Pydantic default

### リスク
- モデル変更時に全ファイルの修正が必要
- デフォルト値の不整合が起きやすい
- どれがソースオブトゥルース（SSOT）か不明確

### 提案
1. SSOT を **`config/settings.toml`** に定め、`base.py` の定数は TOML から動的読み取りに変更する
2. `models.yaml` の役割を明確化する（削除 or TOML に統合）
3. デフォルト値は Pydantic モデルのみに定義し、重複を排除する

---

## 優先順位 第7位: プロンプトテンプレート管理体制の確立

### 現在の問題
`prompts/` ディレクトリに **80以上の `.j2` ファイル** がフラットに配置されている。
- ファイル命名規則が不統一（`_prompt.j2` / `.j2` / 拡張子なし が混在）
- フロントマターによるバージョン管理が一部で始まっているが全体に浸透していない
- テンプレート間の依存関係（`{% include "..." %}`）が追跡困難

### リスク
- 使われていないテンプレートの特定が困難
- テンプレートの変更影響範囲が把握できない
- オンボーディングコストが高い

### 提案
1. テンプレートカテゴリごとにサブディレクトリ分割（`audit/`, `drafting/`, `polishing/` など）
2. 全テンプレートにフロントマター（version, description, variables）を統一フォーマットで付与
3. 未使用テンプレートのスキャンツールを導入
4. 命名規則を統一的に定める（例: `kebab-case.j2`）

---

## 優先順位 第8位: ファイル監視 + ホットリロードのテスト容易性改善

### 現在の問題
[`config/file_watcher.py`](../config/file_watcher.py) の `ConfigFileHandler` が `UIStateStore` に直接依存しており、ファイル監視機能を単体テストできない。

### リスク
- ホットリロードのテストがなく、リグレッションを検出できない
- 内部で `time.sleep(2)` しており、テスト時間が無駄に長くなる

### 提案
1. `FileSystemEventHandler` を純粋な「変更検知 → コールバック実行」に分離
2. `UIStateStore` への依存をコールバック注入方式に変更
3. テスト用に `FakeFileSystemEventHandler` と `ObserverStub` を提供

---

## 優先順位 第9位: 重複データファイルの統合（tropes.json）

### 現在の問題
- [`config/tropes.json`](../config/tropes.json) と [`config/data/archetypes.json`](../config/data/archetypes.json) でトロープ（ざまぁ、無双等）が重複定義されている
- ドメインプロファイル（`config/domain_profiles/*.json`）には別フォーマットで情報が存在
- [`config/domain_profile_manager.py`](../config/domain_profile_manager.py:66) にはハードコードされたプロファイル定義が残っている

### リスク
- トロープ追加時に2-3ファイルの修正が必要
- JSON と Python 定数の二重管理
- データ間の整合性を保証する仕組みがない

### 提案
1. `config/domain_profile_manager.py` のハードコードを削除し、全プロファイルを JSON/YAML ファイルに移動する
2. `config/data/` 配下の重複キーを統合スキーマで管理する
3. 設定バリデーションでクロスファイル参照の整合性チェックを追加する

---

## サマリ：期待効果

| # | 提案 | 期待効果 | 難易度 | リスク低減度 |
|---|------|---------|--------|------------|
| 1 | 設定モデル重複排除 | ★★★★★ | 中 | 高 |
| 2 | Streamlit分離 | ★★★★ | 高 | 高 |
| 3 | インラインテンプレート分離 | ★★★ | 低 | 中 |
| 4 | __init__.py整理 | ★★★ | 低 | 中 |
| 5 | バリデーションパイプライン統一 | ★★★★ | 中 | 高 |
| 6 | 定数重複統合 | ★★★★ | 中 | 中 |
| 7 | テンプレート管理体制 | ★★★ | 中 | 中 |
| 8 | ファイル監視テスト容易化 | ★★ | 低 | 低 |
| 9 | データファイル統合 | ★★ | 低 | 低 |
