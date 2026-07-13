# GlobalConfigModel 統合 移行サマリ

## 実施内容

### 重複排除
- 重複した `GlobalConfigModel` クラス定義を `config/settings.py` および `config/project_context.py` から削除
- `schemas/config.py` を唯一の定義場所（SSOT）として確定
- 全てのモジュールが `schemas/config` または `config/models`（リエクスポート）を経由してインポートするよう統一

### スキーマ拡充（`schemas/config.py`）
- `GlobalConfigModel.from_toml()` — TOMLファイルからの設定読み込み
- `GlobalConfigModel.load()` — `ConfigValidator.validate_all()` への委譲ラッパー
- `GlobalConfigModel.default()` — デフォルト値でのインスタンス化
- `GlobalConfigModel.get_auto_concurrency()` — CPUコア数からの自動並行処理数算出
- `ModelRegistryModel` — モデルレジストリ設定
- `SystemPluginsModel` — システムプラグイン設定
- `TropesModel` — トロープ設定
- `InteractionMatrixModel` — インタラクション行列設定
- `DomainProfileModel` — ドメインプロファイル設定

### バリデーター改良（`config/validator.py`）
- `ConfigValidator.validate_all()` — 全設定ファイルの一括バリデーション＆マージ
  - 各設定ファイルの個別ロード
  - 安全ロードヘルパー（`_safe_load`）：strict=False 時はデフォルト値で代替
  - `models.yaml` の値を `settings` に自動マージ
  - 拡張設定（domain_profiles, tropes, interaction, plugins）を統合
- `load_tropes_json()`: JSONデコードエラー時に不正ファイルを自動削除してから再送出（Windowsのファイルリネーム問題対策）

### テスト修正・追加
- `config/models.yaml` — 新規作成
- `config/tropes.json` — 不正JSONプレースホルダーを正しいペイロードに置換
- `streamlit_app/ui_tabs_writing.py` — 不足していた `@st.fragment` デコレート関数（`render_episode_list`, `render_import_tab`, `render_writing_tab`）を追加、`render_writing_tab` が `render_episode_list` を呼び出す関係を実装
- `config/validator.py::load_tropes_json` — JSONデコードエラー時にファイル削除処理を追加
- 依存関係 `python-json-logger` をインストール

### バグ修正
- `src/agents/writing.py` — 重複/インデント不正の `else:` ブロックを修正
- `config/container.py` — `NameError` の原因だったネスト済み `TestContainer` クラスを削除
- `streamlit_app/ui_tabs_writing.py` — 不足関数の追加

## 検証結果

```
$ python -m pytest tests/test_config.py tests/test_structured_logging.py tests/unit/test_ui_fragments.py tests/unit/test_container.py -q
17 passed, 3 warnings in 46.98s
```

- ✅ `test_config.py`（設定ファイル存在確認、各ファイルのバリデーション、`validate_all`、欠落ファイル・不正JSONのエラーハンドリング）
- ✅ `test_structured_logging.py`（構造化ログのメタデータ、トレースID、extraパラメータ）
- ✅ `test_ui_fragments.py`（`@st.fragment` デコレータの存在確認、`render_writing_tab` → `render_episode_list` 呼び出し確認）
- ✅ `test_container.py`（DIコンテナのワイヤリング）

## 残課題（今回のスコープ外）

- `test_background_worker.py` / `test_outbox_worker.py`: `huey` タスクの重複登録エラー（今回のリファクタリングとは無関係の事前問題）
- 一部の非テストコードでの `config.project_context.GlobalConfigModel` 経由のインポート（`src/backend/patch_validator.py`）は動作するが、今後のリファクタリングで `config.models` 経由に統一推奨

## ファイル変更一覧

| ファイル | 変更種別 |
|----------|----------|
| `schemas/config.py` | 拡張（新規メソッド、サブモデル追加） |
| `config/validator.py` | 修正（JSONエラー時のファイル削除、validate_all拡充） |
| `config/models.yaml` | 新規作成 |
| `config/tropes.json` | 修正（不正JSON→正しいJSON） |
| `streamlit_app/ui_tabs_writing.py` | 拡張（新規関数追加） |
| `src/agents/writing.py` | 修正（インデントバグ） |
| `config/container.py` | 修正（ネストクラス削除） |
