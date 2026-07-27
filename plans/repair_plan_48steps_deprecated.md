# AutoNovel プロジェクト修復 実装計画（48ステップ）

## 前提・前提確認事項
- **本番ルート**: `D:\autonovel\autonovel` を正とする。
- **ルート直下 `D:\autonovel\`** はレガシー/誤配置（空 `frontend`、旧 `docker-compose.yml`、散乱スクリプト）。整理後は本番ルートのみ使用。
- **Python**: `py`（Windows py launcher）+ 仮想環境 `.venv` を使用。
- **コマンド**: 各ステップは1ファイル/1コマンド単位で完結し、低性能LLMでも逐次実行可能。

## フェーズ構成
- フェーズA（ステップ1-6）: pytest 実行環境の正常化
- フェーズB（ステップ7-12）: Ruff/lint 低減の準備
- フェーズC（ステップ13-20）: 静的解析（mypy）の正常化
- フェーズD（ステップ21-30）: Docker/前端の起動可能性確保
- フェーズE（ステップ31-40）: ルート二重化の解消
- フェーズF（ステップ41-48）: 検証と仕上げ

---

## フェーズA: pytest 実行環境の正常化

### ステップ1: temp/test_models.py の無害化
- **対象**: `autonovel/temp/test_models.py`
- **作業**: トップレベルの `sys.exit(1)` を `raise SystemExit(1)` に変更（即時クラッシュ回避）。さらに `if __name__ == "__main__":` ガードで全体を囲み、import 時に実行されないようにする。
- **コード例**:
  ```python
  if __name__ == "__main__":
      # 既存の try/except ブロック全体をこの中にインデントして移動
      ...
  ```
- **確認**: `py -m pytest --collect-only` が INTERNALERROR なく完了するか。

### ステップ2: temp/ ディレクトリ全体を pytest 収集対象から除外
- **対象**: `autonovel/pyproject.toml`（新規追記部）
- **作業**: `[tool.pytest.ini_options]` セクションを追加し、`testpaths` と `norecursedirs` / `collect_ignore` を設定。
- **追記内容**:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  norecursedirs = ["temp", "archive", "backup", "kaku_hegemony.egg-info", ".mypy_cache", ".ruff_cache", "node_modules"]
  addopts = "-p no:cacheprovider --import-mode=importlib"
  ```
- **確認**: `py -m pytest --collect-only` で temp 配下が収集されない。

### ステップ3: conftest.py の作成（sys.path 調整）
- **対象**: `autonovel/tests/conftest.py`（存在しなければ新規）
- **作業**: プロジェクトルートを `sys.path` に追加する最小限の setup。
- **コード例**:
  ```python
  import os, sys
  ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  if ROOT not in sys.path:
      sys.path.insert(0, ROOT)
  ```
- **確認**: `py -m pytest --collect-only` で ImportError が減少。

### ステップ4: 重複 test_imports.py のリネーム
- **対象**:
  - `autonovel/archive/legacy_scripts/backups/scratch_archive/test_imports.py` → `test_imports_scratch_archive.py`
  - `autonovel/archive/legacy_scripts/backups/old_scratch/test_imports.py` → `test_imports_old_scratch.py`
- **作業**: `Move-Item` でリネーム。
- **確認**: 重複ファイル名の一覧 `Get-ChildItem -Recurse -Filter test_imports.py` が1件以下になる（アクティブな tests 配下のみ）。

### ステップ5: archive/backup をツール類の対象から除外（pt1: pyproject.toml mypy 编集）
- **対象**: `autonovel/pyproject.toml` の `[tool.mypy]`
- **作業**: `exclude` 設定を追加。
- **追記**:
  ```toml
  exclude = ["archive/", "backup/", "temp/", "tests/.*legacy", "kaku_hegemony.egg-info/"]
  ```
- **確認**: `py -m mypy src` が archive 配下を走査しない。

### ステップ6: ruff の除外設定追加
- **対象**: `autonovel/pyproject.toml` の `[tool.ruff]`
- **作業**: `extend-exclude` または初期 `exclude` を設定。
- **追記**:
  ```toml
  [tool.ruff]
  extend-exclude = ["archive", "backup", "temp", "kaku_hegemony.egg-info", ".mypy_cache", "node_modules", "tests/.*legacy"]
  ```
- **確認**: `py -m ruff check .` の対象ファイル数が大幅減少（数千→数百程度へ）。エラー総数ログを `ruff_before.txt` に控える。

---

## フェーズB: Ruff/lint 低減（高影響箇所の個別修正）

### ステップ7: state.py の get_runtime 重複定義の調査
- **対象**: レポート指摘の `streamlit_app/state.py`（存在しない場合 `src` 配下を検索）
- **作業**: `grep -rn "def get_runtime"` で重複箇所を特定し、ファイルを行番号付きで読込。
- **確認**: 重複があればどの行かメモ。存在しなければ「対象外」と記録。

### ステップ8: 重複定義 get_runtime の統合
- **対象**: ステップ7で特定したファイル
- **作業**: 後の定義（Line 374側）を削除するか、意図的に上書きなら後方に `# noqa: F811` を付与。原則は削除し、2番目の実装が正しければ1番目を差し替え。
- **確認**: `py -m ruff check <file>` で F811 が消失。

### ステップ9: test_api_client_http_semantics.py の重複テスト関数の解消
- **対象**: `autonovel/tests/integration/test_api_client_http_semantics.py`
- **作業**: Line 44 と Line 62 にある `test_delete_request_uses_params_not_json()` のうち、意図が同じなら片方削除、異なる観点なら `test_delete_request_uses_params_not_json_via_xxx()` にリネーム。
- **確認**: `py -m ruff check <file>` で F811 消失。

### ステップ10: streamlit_app/app.py の未使用 service 変数の削除
- **対象**: `autonovel/streamlit_app/app.py` Line 77（存在確認後）
- **作業**: `service = EngineService.get_instance(api_key=api_key)` を削除、または `EngineService.get_instance(api_key=api_key)` のみ呼出（副作用目的なら `_ =` ではなくコメントで意图明示）。
- **確認**: `py -m ruff check <file>` で F841 消失。

### ステップ11: backend_launcher.py の未使用 entry 変数の解消
- **対象**: `autonovel/streamlit_app/backend_launcher.py` Line 56
- **作業**: `entry = _find_backend_entrypoint()` が未使用なら削除、または後続で使用するなら接続先に統合。
- **確認**: F841 消失。

### ステップ12: easy-mode.py の未使用 BaseModel import 削除
- **対象**: `src/backend/routers/easy-mode.py` Line 2
- **作業**: `from pydantic import BaseModel` 行を削除（他で未使用の場合）。
- **確認**: `py -m ruff check src/backend/routers/easy-mode.py` で F401 消失。

---

## フェーズC: mypy 解析の正常化

### ステップ13: mypy 実行とエラー集計
- **作業**: `py -m mypy src > mypy_out.txt 2>&1` を実行し、結果をファイル出力。
- **確認**: INTERNALERROR なく完了、または通常の型エラー一覧が出力される。

### ステップ14: test_imports リネーム後の再確認
- **作業**: `grep "test_imports" mypy_out.txt` で重複モジュール起因エラーが消えたか確認。
- **確認**: 該当エラー行が0件。

### ステップ15: pyproject.toml の disallow_untyped_defs を一時緩和
- **対象**: `autonovel/pyproject.toml` Line 8
- **作業**: `disallow_untyped_defs = true` → `disallow_untyped_defs = false` に一時変更（修復完了後元に戻す、ステップ47）。
- **確認**: mypy のエラー総数が大きく減少。

### ステップ16: src 配下の __init__.py 確認
- **作業**: `Get-ChildItem -Recurse -Filter __init__.py src` を実行し、各パッケージの `__init__.py` が存在するか確認。不足があれば空ファイル作成。
- **確認**: mypy の `"Module has no attribute"` 系エラーが減少。

### ステップ17: 明らかな型注記の欠落を補完（一部）
- **対象**: mypy_out.txt で最頻出する関数10箇所
- **作業**: 戻り値型 `-> None` や引数型を追記。1関数ずつ個別コミット想定。
- **確認**: 都度 `py -m mypy <file>` で該当エラー消失。

### ステップ18: ignore_missing_imports の確認
- **対象**: pyproject.toml Line 14, overrides 行18-24
- **作業**: streamlit, prompts 以外で欠落 import があるか `mypy_out.txt` を確認し、必要 override を追加。
- **確認**: import 起因エラーが 0 または既知の ignore 行のみ。

### ステップ19: mypy の CI 用コマンド固定化
- **作業**: `scripts/typecheck.ps1` を新規作成。
  ```powershell
  Set-Location $PSScriptRoot\..
  py -m mypy src
  ```
- **確認**: `./scripts/typecheck.ps1` 実行で mypy が走る。

### ステップ20: ruff の isort 自動適用（限定）
- **作業**: `py -m ruff check --select I --fix src tests` を実行。E402 は手動判断のためこのステップでは isort のみ。
- **確認**: import 順序違反 I001 が大幅減少。E402 は残り。

---

## フェーズD: Docker/前端の起動可能性確保

### ステップ21: ルート docker-compose.yml の整理方針決定
- **対象**: `D:\autonovel\docker-compose.yml`（ルート側）
- **作業**: ルート側は削除対象と判断（フェーズEで実施）。本ステップでは `autonovel/docker-compose.yml` を正とする方針を文書化（このファイル末尾にメモ追記はしない）。
- **確認**: 方針をステップ31の入力にする。

### ステップ22: autonovel/frontend/ の実態確認
- **作業**: `Get-ChildItem autonovel\frontend -Force` を実行、Dockerfile/package.json/vite.config.ts の有無を確認。node_modules のみ存在なら application コード未配置と判断。
- **確認**: 結果をメモ。frontend が未実装か確認。

### ステップ23: docker-compose.yml から frontend サービスを一時切り離す
- **対象**: `autonovel/docker-compose.yml` Line 34-61
- **作業**: `frontend-dev`, `frontend-prod` サービスブロックを `docker-compose.override.yml.yml` や別ファイルに退避するか、コメント化。 essentials は backend + worker のみとする。
- **コード例**:
  ```yaml
  # frontend services temporarily disabled (frontend app not yet provided).
  # See step 22 investigation notes. Re-enable when frontend/ is populated.
  ```
- **確認**: `docker compose config` がエラーなく表示（frontend ビルド未参照）。

### ステップ24: root 側空 frontend の削除
- **対象**: `D:\autonovel\frontend`（空ディレクトリ）
- **作業**: `Remove-Item -LiteralPath "D:\autonovel\frontend" -Recurse -Force`（念のため中身0件を再確認後）。
- **確認**: `Test-Path D:\autonovel\frontend` → False。

### ステップ25: pytest 用の pytest.ini との併存確認
- **作業**: `pyproject.toml` の `[tool.pytest.ini_options]` と既存 `pytest.ini` / `setup.cfg` の重複を確認。重複があれば `pytest.ini` 側を削除して pyproject に一本化。
- **確認**: `py -m pytest --co -q` で WARNING なし。

### ステップ26: アプリ起動.bat の参照先確認
- **対象**: `D:\autonovel\アプリ起動.bat`
- **作業**: `cd /d "%~dp0autonovel"` で autonovel 配下の compose を呼んでいることを確認。方針Eで bat 自体を移動/置き換え（ステップ37）。
- **確認**: bat の挙動が正しい本番ルートを指す。

### ステップ27: Dockerfile（backend用）の存在確認
- **対象**: `autonovel/Dockerfile`
- **作業**: ファイル存在 + 内容確認。`uvicorn` 起動要件（依存）が requirements に揃うか確認。
- **確認**: backend サービス単体なら `docker compose build backend` が成功（実行は任意）。

### ステップ28: requirements / 依存関係の確認
- **対象**: `autonovel/requirements*.txt`, `pyproject.toml` の `[project]` dependencies
- **作業**: 依存一覧を確認し、Dockerfile の `pip install` 対象と整合するか。
- **確認**: 主要パッケージ（fastapi, uvicorn, huey, streamlit, pydantic）が過不足なく記載。

### ステップ29: docker compose backend の起動テスト（dry-run）
- **作業**: `docker compose -f autonovel\docker-compose.yml config` を実行し、YAML 構文エラーを検出。実ビルドは環境次第なので省略可。
- **確認**: 構文 OK。

### ステップ30: 健全性チェック health エンドポイント確認
- **対象**: `src/backend/server.py` に `/health` ルート存在確認
- **作業**: `grep -n "health" src/backend/server.py` で確認。未実装なら追加（FastAPI の最小ルート）。
- **確認**: ステップ29 のヘルスチェックが機能する見込み。

---

## フェーズE: ルート二重化の解消

### ステップ31: レガシーファイル群（ルート直下）の棚卸
- **対象**: `D:\autonovel\`
  - `tmp_replace_normalize.py`, `mypy_errors.txt`, `mypy_out.txt`, `ruff_e722.txt`
  - `docker-compose.yml`（ルート側）
  - `frontend/`（ステップ24で削除済）
- **作業**: 一覧化して `D:\autonovel\backup\` を新規作成し移動（削除はしない）。
- **コマンド例**:
  ```powershell
  New-Item -ItemType Directory -Path D:\autonovel\backup -Force
  Move-Item D:\autonovel\tmp_replace_normalize.py D:\autonovel\backup\
  Move-Item D:\autonovel\mypy_errors.txt D:\autonovel\backup\
  Move-Item D:\autonovel\mypy_out.txt D:\autonovel\backup\
  Move-Item D:\autonovel\ruff_e722.txt D:\autonovel\backup\
  Move-Item D:\autonovel\docker-compose.yml D:\autonovel\backup\docker-compose.root.yml
  ```
- **確認**: `Get-ChildItem D:\autonovel -File` が `.bat` 等のみ。

### ステップ32: ルート .git の取扱決定
- **作業**: `Test-Path D:\autonovel\.git` と `Test-Path D:\autonovel\autonovel\.git` を確認。両方ある場合、どちらが主流履歴か `git log --oneline | Select-Object -First 5` で比較。
- **確認**: 主流を決定。非主流は `backup/` に退避準備。

### ステップ33: ルート側空ディレクトリ（src/frontend等）の削除
- **作業**: `Test-Path` で存在確認の上、空であれば削除。非空なら中身を `backup/` に移動してから削除。
- **確認**: `Get-ChildItem D:\autonovel -Directory` が `autonovel`, `backup` のみ。

### ステップ34: アプリ起動.bat の移動と参照修正
- **対象**: `D:\autonovel\アプリ起動.bat`
- **作業**: 内容を `D:\autonovel\autonovel\アプリ起動.bat` に複製し、内部 `cd /d "%~dp0autonovel"` を `cd /d "%~dp0"` に変更。元ファイルは `backup/` へ。
- **確認**: 新 bat をダブルクリックで autonovel 配下の compose が呼ばれる。

### ステップ35: 非主流 .git の退避
- **対象**: ステップ32 で非主流と判定した `.git`
- **作業**: `Move-Item D:\autonovel\.git D:\autonovel\backup\repo_root.git.bak` （名前衝突回避）。
- **確認**: `Test-Path D:\autonovel\.git` → False。`D:\autonovel\autonovel\.git` は維持。

### ステップ36: ルートに README を新規作成し運用ルート明示
- **対象**: `D:\autonovel\README.md`（新規）
- **作業**: 「本番ルートは `./autonovel/` です」と1段落で明記。
- **確認**: ファイル存在。

### ステップ37: アプリ起動.bat の動作確認
- **作業**: テキストで dry-run 確認（クリック実行はユーザ判断）。`cd` 先が存在するか Test-Path。
- **確認**: 参照先 `D:\autonovel\autonovel\docker-compose.yml` 存在。

### ステップ38: autonovel 配下の補助スクリプト整理
- **対象**: `autonovel/scripts/` の分類。古い lint 修正補助スクリプト等があれば `autonovel/archive/scripts/` へ移動。
- **確認**: `scripts/` には現用の `typecheck.ps1`（ステップ19）等のみ。

### ステップ39: egg-info / cache のクリンナップ
- **作業**:
  ```powershell
  Remove-Item -Recurse -Force autonovel\kaku_hegemony.egg-info
  Remove-Item -Recurse -Force autonovel\.mypy_cache
  Remove-Item -Recurse -Force autonovel\.ruff_cache
  Remove-Item -Recurse -Force autonovel\.pytest_cache
  ```
- **確認**: `py -m mypy src` がキャッシュ再生成から正常開始。

### ステップ40: backup/ の .gitignore 確認
- **対象**: `autonovel/.gitignore`
- **作業**: `backup/`, `*.bak`, 作成したキャッシュ類が ignore 対象か確認。不足分を追記。
- **確認**: `git status`（Working treeが整合）で backup/ が一覧に出ない。

---

## フェーズF: 検証と仕上げ

### ステップ41: 全体 pytest 再実行
- **作業**: `py -m pytest --collect-only` → 収集成否、その後 `py -m pytest` を実行（時間次第で `-x` 付き最初失敗で停止）。結果を `tests_results_after.txt` 保存。
- **確認**: INTERNALERROR なし、収集エラー 0 件。

### ステップ42: ruff 再実行と前後比較
- **作業**: `py -m ruff check src tests streamlit_app > ruff_after.txt 2>&1`。`ruff_before.txt`（ステップ6）と件数比較。
- **確認**: エラー総数が大幅減少（数千→数十以下目安）。

### ステップ43: mypy 再実行
- **作業**: `py -m mypy src > mypy_after.txt 2>&1`
- **確認**: INTERNALERROR なし。残エラー数を記録（ステップ47で strict 戻す前のベースライン）。

### ステップ44: docker compose config の最終確認
- **作業**: `docker compose -f autonovel\docker-compose.yml config`
- **確認**: YAML 構文 OK、frontend は無効化されている。

### ステップ45: ルート構造の最終点検
- **作業**: `Get-ChildItem D:\autonovel` と `Get-ChildItem D:\autonovel\autonovel` を表示し、二重化が解消されたか目視。
- **確認**: ルートは `autonovel/`, `backup/`, `README.md`, `アプリ起動.bat`（ルート側、バックアップ済なら alate） のみ。

### ステップ46: 修復レポート（軽量）の作成
- **対象**: `autonovel/plans/repair_report.md`（新規）
- **作業**: 各フェーズの成果、残課題（未解決の mypy/ruff 残数等）を箇条書きで記録。
- **確認**: ファイル存在。

### ステップ47: strict 設定の段階的復元
- **対象**: `autonovel/pyproject.toml` Line 8
- **作業**: `disallow_untyped_defs = false` → `true` に戻す。残エラーが多く `error` で止まる場合は `warn` 運用にするか、`disable_error_code = ["attr-defined", "no-untyped-def"]` を一時採用（この場合コメントで理由明記）。
- **確認**: `py -m mypy src` が終了コード0か1（エラーあり）で完走。INTERNALERRORでないこと。

### ステップ48: 最終統合確認スクリプトの新規
- **対象**: `autonovel/scripts/verify_all.ps1`（新規）
- **内容**:
  ```powershell
  Set-Location $PSScriptRoot\..
  Write-Host "=== ruff ==="
  py -m ruff check src tests
  Write-Host "=== mypy ==="
  py -m mypy src
  Write-Host "=== pytest collect ==="
  py -m pytest --collect-only -q
  Write-Host "=== done ==="
  ```
- **確認**: `./scripts/verify_all.ps1` 実行で3ツールが順次走り、結果が一覧できる。

---

## ロールバック方針
- 各ステップ実行前に該当ファイルがGit管理下なら commit（小さく）。バックアップ系の移動は `backup/` に退避し削除しない。
- 問題発生時は直前の commit に `git restore` で戻す。
- strict 設定戻し（ステップ47）で大崩れする場合は `disallow_untyped_defs = false` のま once とし、次サイクルで型注記を追加。

## 完了定義（Definition of Done）
1. `py -m pytest --collect-only` が INTERNALERROR なく完走。
2. `py -m mypy src` が INTERNALERROR なく完走。
3. `docker compose -f autonovel\docker-compose.yml config` が構文 OK。
4. `D:\autonovel` 直下が `autonovel/`, `backup/`, `README.md` のみ。
5. `scripts/verify_all.ps1` が全工程を通して完走。
