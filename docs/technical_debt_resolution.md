# 技術的負債の解消：実装報告

## 1. テンプレート管理体制の確立
### 変更内容
- **ディレクトリ構造の階層化**: `prompts/` 直下にフラットに配置されていた80以上の `.j2` ファイルを、役割に基づいた5つのカテゴリに整理しました。
  - `prompts/templates/audit/`: 監査・レビュー用
  - `prompts/templates/narrative/`: 物語構成・生成用
  - `prompts/templates/persona/`: キャラクター・ペルソナ定義用
  - `prompts/templates/polish/`: ブラッシュアップ・推敲用
  - `prompts/templates/utility/`: 汎用ツール・補助用
- **読み込みロジックの改善**: [`prompts/registry.py`](prompts/registry.py) の `PromptRegistry` を修正し、`FileSystemLoader` が `prompts/templates/` 以下のサブディレクトリを再帰的に検索するように変更しました。これにより、既存のコードにあるテンプレート名による呼び出しを維持したまま、物理的なディレクトリ構造を整理することができました（後方互換性の維持）。

## 2. ファイル監視 (File Watcher) のテスト容易性改善
### 変更内容
- **依存性の切り離し**: `config/file_watcher.py` において、`UIStateStore` や `streamlit` への直接的な依存を排除しました。
- **Notifier プロトコルの導入**: `AppNotifier` という `typing.Protocol` を定義し、通知とリロード処理を抽象化しました。
- **依存性注入 (DI)**: `ConfigFileHandler` および `ConfigFileWatcher` が `AppNotifier` インターフェースを介して動作するようにリファクタリングし、本番環境用には `DefaultNotifier` を注入するようにしました。
- **単体テストの実装**: `tests/unit/test_file_watcher.py` を作成し、UIなしでファイル変更検知とコールバックが正しく動作することを検証しました。

## 3. データファイル (tropes.json / archetypes.json) の統合
### 変更内容
- **重複分析と統合**: `config/tropes.json` と `config/data/archetypes.json` の間で重複していたトロープ（物語の定番要素）データを分析しました。
- **単一ソース化**: `merge_tropes.py` スクリプトを作成し、`archetypes.json` 内の `PLOT_STRUCTURES` や `STORY_ARCHETYPES` から抽出した全トロープを `config/tropes.json` に集約しました。
- **整合性の確保**: 統合後の `config/tropes.json` を用いて、`ConfigValidator` を含む設定ファイルの読み込みテストを行い、正常に動作することを確認しました。

## 検証結果
- **テンプレート読み込み**: `pytest tests/test_prompts.py` により、新構造への移行後も正常にテンプレートがレンダリングされることを確認。
- **ファイル監視**: `pytest tests/unit/test_file_watcher.py` により、依存性排除後のロジックが正常に動作することを確認。
- **データ整合性**: `pytest tests/test_config.py` により、統合後の `tropes.json` が正しくバリデーションを通過することを確認。
