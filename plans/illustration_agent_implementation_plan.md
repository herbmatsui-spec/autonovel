# イラスト作成サブエージェント – 即時対応5項目 実装計画書

## 目的
以下の5つの緊急課題を解消し、CI が正常に通過し、プロダクション環境での動作を保証する。
1. テストファイルの import パス修正
2. ルーターでの `AppContainer` 未 import の修正
3. `ImageService._save_image()` の URL 正規化バグ修正
4. `apply_safety_modifier` の安全判定ロジック統一
5. 改善計画書（24ステップ）の実装・検証（対象は上記5項目）

---

## 1. テスト import パス修正
### 背景
[`tests/test_illustration_agent.py`](tests/test_illustration_agent.py:4) が `autonovel.src.*` を使用しており、CI 環境で `ModuleNotFoundError` を引き起こす。
### 変更内容
- **対象行**: `tests/test_illustration_agent.py:4-6`
- **修正**: `autonovel.src.agents.illustration_agent` → `src.agents.illustration_agent`
  同様に `autonovel.src.models.illustration` → `src.models.illustration`
- **コミットメッセージ例**: `fix: test_illustration_agent import path to src.*`
### 手順
1. `tests/test_illustration_agent.py` を開く。
2. 行 4‑6 の import 文を置換:
   ```diff
   - from autonovel.src.agents.illustration_agent import IllustrationAgent
   - from autonovel.src.models.illustration import (
   + from src.agents.illustration_agent import IllustrationAgent
   + from src.models.illustration import (
   ```
3. 保存し、`pytest -q` でテストがパスすることを確認。
4. CI パイプラインでテストが緑になることを確認。

---

## 2. ルーターの `AppContainer` import 追加
### 背景
[`src/backend/routers/illustrations.py`](src/backend/routers/illustrations.py:18) で `AppContainer` が未定義のため、リクエスト処理時に `NameError` が発生。
### 変更内容
- **追加 import**: `from src.core.container.app import AppContainer`
- **対象位置**: ファイル冒頭、他の import 文の直後。
### 手順
1. `src/backend/routers/illustrations.py` を開く。
2. 既存 import 文の下に以下を追記:
   ```python
   from src.core.container.app import AppContainer
   ```
3. 保存し、`uvicorn`／テストサーバーで `/generate` エンドポイントが正常に動作することをローカルで確認。
4. `pytest -q tests/test_illustration_features.py::test_illustration_router`（存在すれば）でエンドポイントテストを実行。

---

## 3. `ImageService._save_image()` の URL 正規化
### 背景
`src/services/image_service.py` の `_save_image` は `return f"/{filepath}"` で返却し、`storage_dir` が `static/illustrations` の場合 `"/static/illustrations/img_x.png"` になるが、先頭スラッシュ二重や相対パスの混在でフロントが画像取得に失敗するリスクがある。
### 変更内容
- **対象行**: `src/services/image_service.py:106`
- **修正**: パスを安全に結合し、先頭スラッシュ1つだけを付与。
  ```diff
  - return f"/{filepath}"
  + normalized_path = f"{save_dir.rstrip('/')}/{filename}"
  + return f"/{normalized_path}"
  ```
- **ユニットテスト追加**: `tests/test_image_service_path.py` で保存ディレクトリとファイル名をモックし、期待 URL `/static/illustrations/img_123.png` が返ることを検証。
### 手順
1. `src/services/image_service.py` を編集。
2. 変更を加える。
3. 新規テストファイル作成し、`pytest -q` で全テストが通過することを確認。

---

## 4. `apply_safety_modifier` の統一ロジック
### 背景
`apply_safety_modifier` は独自の `try/except` で R15 判定を行い、`model_selector.is_r15` が既に存在するため重複。
### 変更内容
- **対象行**: `src/services/illustration/prompts.py` の 115‑118 行。
- **修正**: `is_r15` をインポートし、ロジックを置換:
  ```diff
  - try:
  -     is_r15 = safety_level.value == SafetyLevel.R15_CONTENT.value
  - except AttributeError:
  -     is_r15 = str(getattr(safety_level, "value", safety_level)) == "R15_CONTENT"
  + from src.services.illustration.model_selector import is_r15
  + is_r15 = is_r15(safety_level)
  ```
- **インポート追加**: ファイル先頭に `from src.services.illustration.model_selector import is_r15` を追加。
### 手順
1. `src/services/illustration/prompts.py` を編集。
2. 変更後、`flake8`/`ruff` で lint が通ることを確認。
3. 既存テスト（安全修飾が期待通り付与されるか）を再実行。

---

## 5. 24ステップ改善計画書の即時実装フェーズ
### スコープ
上記 **1‑4** の実装を完了し、CI が緑になることを **即時フェーズ** とする。残りのステップ（コード品質、フォールバックプロンプト、進捗分母、フラグ統一等）は次フェーズで着手。
### 完了基準 (Definition of Done)
1. `git diff` が 1‑4 の変更のみを含むこと。
2. `pytest -q` が **100%** パス。
3. `ruff check src/ tests/` がエラー 0。
4. `mypy src/` がエラー 0。
5. ローカルサーバー起動 (`uvicorn src.backend.server:app`) で `/generate` エンドポイントが 200 応答を返す。
6. CI パイプライン（GitHub Actions）でビルド・テストが成功する。
### スケジュール
| 日付 | タスク | 担当 |
|---|---|---|
| Day 1 (08:00‑12:00) | テスト import 修正 | 開発者 A |
| Day 1 (13:00‑15:00) | ルーター AppContainer import 追加 | 開発者 B |
| Day 1 (15:30‑17:00) | `_save_image` 正規化実装 & テスト追加 | 開発者 C |
| Day 2 (09:00‑11:00) | `apply_safety_modifier` refactor | 開発者 D |
| Day 2 (11:30‑12:30) | すべての変更をローカルで統合テスト | 全員 |
| Day 2 (13:30‑15:00) | CI デプロイ確認 & ドキュメント更新 | DevOps |

---

## 付録: 変更対象ファイルと行番号マッピング
| ファイル | 行番号 | 変更概要 |
|---|---|---|
| [`tests/test_illustration_agent.py`](tests/test_illustration_agent.py:4) | 4‑6 | import パス修正 |
| [`src/backend/routers/illustrations.py`](src/backend/routers/illustrations.py:18) | 18 | `AppContainer` import 追加 |
| [`src/services/image_service.py`](src/services/image_service.py:106) | 106 | URL 正規化ロジック置換 |
| [`src/services/illustration/prompts.py`](src/services/illustration/prompts.py:115) | 115‑118 | `is_r15` へ置換、インポート追加 |
| [`src/services/illustration/model_selector.py`](src/services/illustration/model_selector.py:34) | 34 | `is_r15` 定義（参照） |

---

## 更新手順まとめ (CLI)
```bash
# 1. 変更を取得
git checkout -b fix/illustration-immediate

# 2. テスト import 修正
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: tests/test_illustration_agent.py
@@
-from autonovel.src.agents.illustration_agent import IllustrationAgent
-from autonovel.src.models.illustration import (
+from src.agents.illustration_agent import IllustrationAgent
+from src.models.illustration import (
*** End Patch
PATCH

# 3. ルーター import 追加
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/backend/routers/illustrations.py
@@
 from src.core.container import make_container
+from src.core.container.app import AppContainer
*** End Patch
PATCH

# 4. _save_image 正規化
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/services/image_service.py
@@
-        return f"/{filepath}"
+        normalized_path = f"{self.storage_dir.rstrip('/')}/{filename}"
+        return f"/{normalized_path}"
*** End Patch
PATCH

# 5. apply_safety_modifier refactor
apply_patch <<'PATCH'
*** Begin Patch
*** Update File: src/services/illustration/prompts.py
@@
-from src.models.illustration import IllustrationType, SafetyLevel
+from src.models.illustration import IllustrationType, SafetyLevel
+from src.services.illustration.model_selector import is_r15
@@
-    try:
-        is_r15 = safety_level.value == SafetyLevel.R15_CONTENT.value
-    except AttributeError:
-        is_r15 = str(getattr(safety_level, "value", safety_level)) == "R15_CONTENT"
+    is_r15 = is_r15(safety_level)
*** End Patch
PATCH
```

上記手順を実行後、`git push -u origin fix/illustration-immediate` で PR を作成し、レビュー・マージを行う。

---

## 次フェーズ（残りの 19 ステップ）
- `_generate_episode` のフォールバックプロンプト強化
- `illustration_workflow.update_progress` の分母動的化
- フラグ名 `enableErotic` / `enable_r15` の統一
- `apply_safety_modifier` の docstring 充実
- `ImageService` の二重 `get_imagen_model_id` 呼び出し簡略化
- `BaseAgent` と `repo` 前提のドキュメント化
- すべての AUTO/モデル解決パスに対するテスト追加
- CI 用の `ruff`/`mypy` 設定更新
- デプロイ環境での環境変数 `GOOGLE_GENAI_API_KEY` 必須チェック追加
- 変更後のリリースノート作成

以上が **即時対応5項目** の詳細実装計画です。