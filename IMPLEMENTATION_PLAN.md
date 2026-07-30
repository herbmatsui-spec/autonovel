# 実装計画書：覇権小説エンジン v3.0 安定化・品質改善

## 背景

技術評価および実機検証の結果、以下の問題が確認された：
1. データベーススキーマ不整合（`internal_state.updated_at` の型不整合）
2. ハードコードされた漏洩APIキーの存在
3. Hueyワーカー内でのインポート不備
4. ProgressState の datetime/文字列不整合
5. CI型検査の非阻止設定による型安全性の未担保
6. 重複リポジトリ層による保守性低下

本計画書は、これらの問題を修正し、ツールを実運用可能な状態にするための詳細な実装手順を定義する。

---

## フェーズ1：クリティカルバグ修正（即時）

### 1.1 データベース DateTime 不整合の修正
**対象**: `save_internal_state` の型不統一

**変更内容**:
- `src/backend/database/core.py`:
  - `save_internal_state` の `updated_at` 引数を `str` → `datetime.datetime` に変更
  - インポートに `from datetime import datetime` を追加
- `src/backend/database/repo_misc.py`:
  - `time.strftime('%Y-%m-%dT%H:%M:%S')` → `datetime.now()` に変更
  - `import time` → `from datetime import datetime` に変更
- `src/backend/server.py`:
  - `time.strftime('%Y-%m-%d %H:%M:%S')` → `datetime.now()` に変更
  - `from datetime import datetime` を追加
- `src/backend/routers/tasks.py`:
  - `time.strftime('%Y-%m-%d %H:%M:%S')` → `datetime.now()` に変更
  - `from datetime import datetime` を追加
- `src/backend/task_helpers.py`:
  - `time.strftime('%Y-%m-%d %H:%M:%S')` → `datetime.now()` に変更
  - `from datetime import datetime` を追加
- `src/backend/background.py`:
  - `datetime.datetime.now().isoformat()` → `datetime.datetime.now()` に変更
  - すでに `datetime` はインポート済みのため、`.isoformat()` を削除するのみ

**検証**: バックエンド起動後、`/api/easy_mode/generate` を実行し、`task_status` の保存が成功することを確認。

**ステータス**: ✅ 完了済み

### 1.2 ハードコードAPIキーの削除
**対象**: レガシーテストスクリプト内の漏洩キー

**変更内容**:
- `archive/legacy_scripts/test_integration.py` の `AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4` を `os.environ.get("GEMINI_API_KEY")` のみに変更
- `archive/legacy_scripts/test_easy_mode.py` の同上
- `archive/legacy_scripts/scratch_debug.py` の同上
- `archive/legacy_scripts/demo_verify.py` の同上
- `archive/legacy_scripts/balance_verify.py` の同上

**検証**: `grep -r "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4" src/` が該当なしになることを確認。

**ステータス**: 実施待ち

### 1.3 Hueyワーカーのインポート不備修正
**対象**: `src/backend/tasks.py`

**変更内容**:
- `save_prompt_metrics` 関数内で `asyncio` が使用されているがインポートされていない
- `import asyncio` を追加

**検証**: Hueyワーカー起動後、定期タスク `save_prompt_metrics` がエラーなく実行されることを確認。

**ステータス**: 実施待ち

---

## フェーズ2：アーキテクチャ改善（短期）

### 2.1 Alembicマイグレーションの再有効化
**現状**: `init_db()` が `Base.metadata.create_all()` でスキーマを作成し、マイグレーションをバイパスしている

**変更内容**:
- `src/backend/database/core.py` の `init_db()` で `command.upgrade("head")` を再有効化
- `create_all` はテスト環境用のフォールバックとして保持
- 本番・開発環境ではマイグレーションを優先

**検証**: 空のDBファイルで起動し、マイグレーションが適用されること、`alembic_version` テーブルが存在することを確認。

**ステータス**: 実施待ち

### 2.2 重複リポジトリ層の統合計画
**現状**: `repo_*.py` と `repositories/*.py` の2層が存在

**変更内容**:
- `src/backend/database/repo_misc.py` など `repo_*.py` を `repositories/*.py` に統一
- またはその逆。どちらを正とするかをADRに記載
- `foreshadow` 関連の dead code を削除

**検証**: `grep -r "repo_plot\|repo_misc\|repo_character" src/` が統一後の層のみを参照することを確認。

**ステータス**: 計画のみ（本実装は要相談）

### 2.3 broad exception handling の具体化
**対象**: 253件の `except Exception`、7件の bare `except`

**変更内容**:
- 各 `except Exception` を、期待される例外型（`LLMUnrecoverableError`、`sqlalchemy.exc.OperationalError` など）に置き換え
- ログ出力の充実（エラー種別、スタックトレース、補助情報）
- 回復不能なエラーは早期に `raise` する方針を徹底

**検証**: 該当箇所の grep 数が減少することを確認。

**ステータス**: 計画のみ

---

## フェーズ3：型安全性・保守性改善（中期）

### 3.1 mypy残余エラーの段階的解消
**現状**: 1,769件の残余エラー

**変更内容**:
- `continue-on-error: true` を `continue-on-error: false` に移行
- エラーをモジュール単位で優先度付けし、`# type: ignore` を正当化
- 100件単位で解消コミットを作成

**検証**: `mypy --config-file pyproject.toml src/` がエラー0で通ることを最終目標。

**ステータス**: 計画のみ

### 3.2 print文のログ置き換え
**対象**: 31件の `print()` 文

**変更内容**:
- `print(f"DEBUG: ...")` → `logger.debug(...)`
- ログレベルとコンテキスト（trace_id等）の付与

**検証**: `grep -r "print(" src/` が該当なしになることを確認。

**ステータス**: 計画のみ

---

## 実行順序

1. **フェーズ1.2, 1.3** を実施（ハードコードキー削除、インポート修正）
2. ユーザーから有効な Gemini API キーを入手
3. **かんたんモード実行**: 1作品、10話、1話3000字
4. 生成結果の検証・レポート作成
5. **フェーズ2, 3** を計画的に実施

---

## 検証手段

- ユニットテスト: `pytest tests/unit -q`
- 型検査: `mypy --config-file pyproject.toml src/ streamlit_app/`
- Lint: `ruff check src/ streamlit_app/ tests/`
- 手動検証: バックエンド + Huey + フロントエンド起動後、`/api/easy_mode/generate` で小説生成が完了することを確認

---

*作成日: 2026-07-16*
