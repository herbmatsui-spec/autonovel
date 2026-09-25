# AutoNovel v5系完成化 実装計画書【T2】
# リポジトリ衛生化・バージョン/仕様完全同期・リリースパッケージング（リグレッション防止含む）

- **文書ID**: PLAN_V5_FINALIZATION_T2_REPO_HYGIENE_12STEPS
- **作成日**: 2026-09-25
- **対象バージョン**: AutoNovel v5.2.0 (v5系最終完成形)
- **関連ドキュメント**: [readme_vs_actual_status.md](file:///e:/hhh/docs/readme_vs_actual_status.md), [PHASE_ROADMAP_MASTER.md](file:///e:/hhh/plans/PHASE_ROADMAP_MASTER.md)

---

## 1. 概要と目的

本計画書は、度重なる機能追加・リファクタリング・検証によってリポジトリ直下に散乱した一時ファイルやデバッグスクリプトを一掃し、バージョン表記の不整合やドキュメントとコードの実態乖離を解消して、**「商用・公開パッケージとしてのクリーンさと品格」**を確立するための実行計画書です。

現在、ルートディレクトリに 8 件の `debug_*.py`、複数の一時ログ（`full_test_result.txt` 等）、および直近で追加された初心者向け自己完結型 HTML デモが未整理のまま置かれています。また、バージョン番号が `5.0.3`, `5.1.0`, `5.1.1`, `5.2.0` と各設定ファイル間で不整合を起こしています。

本計画では、リポジトリの物理的な衛生化、バージョンの `v5.2.0` への統一、README の最新同期を行い、さらに**「リポジトリ衛生とバージョン整合性を恒久的に保証するリグレッション防止テスト」**を導入します。

---

## 2. 12の実行ステップ

```
[ファイル整理・隔離]           [バージョン・ドキュメント同期]                              [衛生リグレッション防止]
Step 1: デバッグファイル退避 ──► Step 4: バージョン完全統一 ──► Step 7: 旧シム完全撤廃  ──► Step 10: バージョン整合性テスト
Step 2: ログ/レポート退避   ──► Step 5: README実態同期    ──► Step 8: scripts整理      ──► Step 11: リポジトリ衛生検査テスト
Step 3: HTMLデモの正規移設  ──► Step 6: 内部ドキュメント整合──► Step 9: gitignore改定    ──► Step 12: クリーンインストール検証
```

### Step 1: ルート直下の一時デバッグスクリプト群のアーカイブ退避
- **対象ファイル**:
  - `analyze_models.py`, `debug_parser.py`, `debug_persist.py`, `debug_regex.py`, `debug_target.py`, `debug_test.py`, `debug_test2.py`, `debug_test3.py`, `debug_unicode.py`, `manual_verification.py`, `final_verification.py`, `test_simple.py`
- **作業内容**:
  1. 上記 12 個のスクリプトを `scripts/archive/debug/` ディレクトリへ移動。
  2. ルートディレクトリから開発時の使い捨て `.py` ファイルを完全に排除。
- **検証コマンド**:
  ```powershell
  Get-ChildItem -Path e:\hhh -Filter "debug_*.py"
  ```
  *(結果が 0 件であること)*

---

### Step 2: 過去のテストログ・一時レポート・中間ファイルのアーカイブ化
- **対象ファイル**:
  - `fail_list.txt`, `fail_now.txt`, `full_test_result.txt`, `test_output.txt`, `json-report.json`, `comparison_table.md`, `regressions_table.md`
- **作業内容**:
  1. これらの中間ファイル・ログを `docs/archive/v5_transition_reports/` へ移動。
  2. ルート直下のファイル一覧を公式ファイル（README, CHANGELOG, Dockerfile等）のみに純化。
- **検証コマンド**:
  ```powershell
  Get-ChildItem -Path e:\hhh -Filter "*.txt"
  ```
  *(ルート直下に一時テキストファイルが存在しないこと)*

---

### Step 3: 初心者向け HTML デモファイル群の専用ディレクトリ（`web/demo/`）への正規配置
- **対象ファイル**:
  - [index.html](file:///e:/hhh/index.html), [script.js](file:///e:/hhh/script.js), [mock-data.js](file:///e:/hhh/mock-data.js), [style.css](file:///e:/hhh/style.css), [README_DEMO.md](file:///e:/hhh/README_DEMO.md), [DEMO_COMPLETION_SUMMARY.md](file:///e:/hhh/DEMO_COMPLETION_SUMMARY.md), [HTML_DEMO_IMPLEMENTATION_PLAN.md](file:///e:/hhh/HTML_DEMO_IMPLEMENTATION_PLAN.md)
- **作業内容**:
  1. ルートから `web/demo/` ディレクトリへ上記ファイルを一括移設。
  2. 相対パス参照（css/js/mock-data）の整合性を確認。
  3. ルートの [README.md](file:///e:/hhh/README.md) に「初心者向けブラウザ単体デモ: `web/demo/index.html`」としての導線を追加。
- **検証コマンド**:
  ```powershell
  Test-Path e:\hhh\web\demo\index.html
  ```

---

### Step 4: バージョン表記の完全統一（`v5.2.0`）
- **対象ファイル**:
  - [pyproject.toml](file:///e:/hhh/pyproject.toml)
  - [src/cli/main.py](file:///e:/hhh/src/cli/main.py)
  - [src/backend/__init__.py](file:///e:/hhh/src/backend/__init__.py)
  - [frontend/package.json](file:///e:/hhh/frontend/package.json)
  - [README.md](file:///e:/hhh/README.md)
- **作業内容**:
  1. `pyproject.toml` -> `version = "5.2.0"`
  2. `src/cli/main.py` -> `__version__ = "5.2.0"`
  3. `src/backend/__init__.py` -> `__version__ = "5.2.0"`
  4. `frontend/package.json` -> `"version": "5.2.0"`
  5. `README.md` バッジおよび記載バージョンを `5.2.0` に一本化（古い 5.0.3, 5.1.0, 5.1.1 の残存を全置換）。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m src.cli.main --version
  ```
  *(出力: `autonovel 5.2.0`)*

---

### Step 5: `README.md` の実態同期（SSOT確立）
- **対象ファイル**:
  - [README.md](file:///e:/hhh/README.md)
- **作業内容**:
  1. [docs/readme_vs_actual_status.md](file:///e:/hhh/docs/readme_vs_actual_status.md) の精査結果に基づき、以下の記述を更新:
     - 執筆基盤が `src.domain.writing` に集約されていることを明記。
     - 統一 CLI `autonovel`（`autonovel check-env`, `autonovel balance`, `autonovel export`）のコマンド解説を追記。
     - 商用拡張機能（動的プラグインシステム、Stripe 課金、JWT/RBAC 認証、OpenTelemetry 監視）を正式な製品特徴として紹介。
- **検証コマンド**:
  ```powershell
  git diff README.md
  ```

---

### Step 6: 内部設計書・API ドキュメントの整合
- **対象ファイル**:
  - [docs/api.md](file:///e:/hhh/docs/api.md)
  - [docs/architecture.md](file:///e:/hhh/docs/architecture.md)
- **作業内容**:
  1. API ドキュメントにおけるエンドポイント（`/api/writing/...`、`/api/billing/...`、`/api/auth/...`、`/easy-mode/...`）の最新ルーティング反映。
  2. アーキテクチャ図の二重化解消（旧 writing_service の記述を `src/domain/writing` へ更新）。
- **検証コマンド**:
  ```powershell
  git status docs/
  ```

---

### Step 7: 廃止済み旧シムの依存ゼロ確認と安全な完全撤廃
- **対象ファイル**:
  - `src/agent/` (旧ディレクトリ)
  - [src/services/age_client.py](file:///e:/hhh/src/services/age_client.py)
  - `src/services/writing_service.py`
- **作業内容**:
  1. プロジェクト全体でこれら旧シムを直接 import している箇所が 0 件であることを ripgrep で再確認。
  2. 既に非推奨（DeprecationWarning）を出している不要シムを完全に削除または退避し、コードベースを身軽化。
- **検証コマンド**:
  ```powershell
  Get-ChildItem -Path src/ -Recurse -Filter "age_client.py"
  ```

---

### Step 8: `scripts/` ディレクトリの整理
- **対象ファイル**:
  - [scripts/](file:///e:/hhh/scripts/)
- **作業内容**:
  1. 重複スクリプトや一時検証スクリプトを `scripts/archive/` に退避。
  2. 正式スクリプト（`check_env.py`, `init_db.py`, `start_local.ps1`, `stop_local.ps1`, `export_openapi.py` 等）の実行権限と引数を整理。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe scripts/check_env.py
  ```

---

### Step 9: `.gitignore` と `.dockerignore` の見直し
- **対象ファイル**:
  - [.gitignore](file:///e:/hhh/.gitignore)
  - [.dockerignore](file:///e:/hhh/.dockerignore)
- **作業内容**:
  1. 今後開発者が作成しがちな `debug_*.py`、`test_*.txt`、`fail_*.txt`、`*.db-journal` などを `.gitignore` に追加。
  2. Docker ビルドコンテキストから `.venv` やドキュメント・アーカイブが除外されるよう `.dockerignore` を厳格化。
- **検証コマンド**:
  ```powershell
  git status --ignored
  ```

---

### Step 10: 【リグレッション防止テスト】バージョン番号整合性自動検査テストの実装
- **新規作成ファイル**:
  - `tests/regression/test_v5_version_consistency.py`
- **テスト設計**:
  * **テスト1**: `test_all_config_versions_match`
    * `pyproject.toml`、`frontend/package.json`、`src/cli/main.py`、`src/backend/__init__.py` のバージョン文字列をパースし、すべてが寸分違わず一致（`5.2.0`）していることをアサート。
  * **テスト2**: `test_readme_version_badge_matches`
    * `README.md` 内のバージョンバッジおよびテキスト記述が現在のプロジェクトバージョンと一致していることをアサート。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_version_consistency.py -v
  ```

---

### Step 11: 【リグレッション防止テスト】リポジトリ衛生・不要ファイル・非推奨インポート禁止テストの実装
- **新規作成ファイル**:
  - `tests/regression/test_v5_repo_cleanliness.py`
- **テスト設計**:
  * **テスト1**: `test_no_debug_scripts_in_root`
    * ルート直下に `debug_*.py` や `manual_*.py`、`*.txt` などのゴミファイルが存在しないことをアサート。
  * **テスト2**: `test_no_deprecated_module_imports`
    * `src/` 配下の全 `.py` ファイルを AST 解析し、廃止された旧モジュール（`src.agent.*`, `age_client`, 旧 `writing_service`）を import している箇所が 1 箇所も存在しないことをアサート。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pytest tests/regression/test_v5_repo_cleanliness.py -v
  ```

---

### Step 12: クリーンインストール・ビルド検証
- **作業内容**:
  1. Python パッケージの editable インストールが警告なく通ることの確認。
  2. フロントエンドのプロダクションビルドが警告なく成功することの確認。
  3. CLI コマンドの正常実行確認。
- **検証コマンド**:
  ```powershell
  .venv\Scripts\python.exe -m pip install -e .
  npm --prefix frontend run build
  autonovel --version
  ```
  *(すべてエラーなく Exit Code 0 で完了すること)*

---

## 3. 完了の定義 (Definition of Done)
1. ルートディレクトリに一時スクリプト・ログ・レポートが 1 件も存在せず、公式ファイルのみで構成されている。
2. 全設定ファイルおよびコード上のバージョンが `5.2.0` で完全に統一されている。
3. `test_v5_version_consistency.py` と `test_v5_repo_cleanliness.py` がパスし、今後のゴミ混入やバージョン不整合を CI で自動検知できる。
