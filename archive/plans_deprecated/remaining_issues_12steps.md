# 未完了問題 実装計画書（12ステップ）

## 対象問題

### 問題1: mypy モジュールの競合エラー
```
src\agents\audit.py: error: Source file found twice under different module names: 
"agents.audit" and "src.agents.audit"
```

**原因:** `d:/autonovel/autonovel/prompts/audit.py` と `d:/autonovel/autonovel/src/agents/audit.py` が共存

### 問題2: test_llm_gateway.py 失敗
```
AttributeError: 'GeminiApiClient' object has no attribute '_lock'
```

**原因:** `retry_decorator.py:130` で `_lock` を参照しているが、`GeminiApiClient` に初期化されていない

### 問題3: Phase F 型注釈欠落の補完（ステップ41-46未完了）

---

## 12ステップ実装計画

### ステップ1: プロジェクト構造の調査
```bash
# 対象ファイルの場所確認
python -c "import os; [print(os.path.join(r,f)) for r,s,fs in os.walk('d:/autonovel/autonovel') for f in fs if f=='audit.py']"
```
**期待結果:**
```
d:/autonovel/autonovel/prompts/audit.py
d:/autonovel/autonovel/src/agents/audit.py
d:/autonovel/autonovel/src/backend/database/repositories/audit.py
d:/autonovel/autonovel/src/models/audit.py
```

### ステップ2: prompts/audit.py の用途調査
```bash
# prompts/audit.py がどこからimportされているか確認
grep -r "from.*prompts.*audit\|import.*prompts.*audit" --include="*.py" d:/autonovel/autonovel
```
**期待結果:** import元のファイル一覧

### ステップ3: prompts/audit.py のリネーム判断
```
根据ステップ2の結果、以下のいずれかを実行:
A) prompts/audit.py を prompts/prompt_audit.py にリネーム（推奨）
B) mypy設定でpromptsを完全除外
```

### ステップ4: prompts/audit.py リネーム実行（必要に応じて）
```bash
# リネームの場合
mv d:/autonovel/autonovel/prompts/audit.py d:/autonovel/autonovel/prompts/prompt_audit.py
```
**注意:** リネーム後はimport文の更新が必要

### ステップ5: retry_decorator.py の _lock 初期化確認
```python
# src/services/retry_decorator.py の GeminiApiClient 関連コードを確認
# 130行目付近: if self._lock is not None:
```
**期待結果:** `_lock` が 어디서初期화되는지 확인

### ステップ6: GeminiApiClient クラスの調査
```python
# src/services/gemini_api_client.py または similar file
# __init__ メソッドで _lock が初期化されているか確認
```
**期待結果:** `_lock` 初期化コードの有無

### ステップ7: _lock 初期化コードの追加（もし欠けている場合）
```python
# GeminiApiClient.__init__ に追加:
import asyncio
self._lock: Optional[asyncio.Lock] = None
```

### ステップ8: test_llm_gateway.py の MagicMock 設定確認
```python
# tests/unit/test_llm_gateway.py
# api_client = GeminiApiClient() の部分で mock_client を設定
```
**期待結果:** Mock設定で _lock が適切にmockされているか確認

### ステップ9: test_llm_gateway.py の修正
```python
# テスト内で api_client._lock = MagicMock() を追加
# または、conftest.py で fixture として設定
```

### ステップ10: 修正後のテスト実行
```bash
cd autonovel && py -m pytest tests/unit/test_llm_gateway.py -v
```
**期待結果:** 2 failed → 2 passed

### ステップ11: mypy 再実行（ステップ4実行後の場合）
```bash
cd autonovel && py -m mypy 2>&1
```
**期待結果:** "Source file found twice" エラーが解消

### ステップ12: 全体テスト実行による最終確認
```bash
cd autonovel && py -m pytest tests/unit/test_async_ui_sync.py tests/unit/test_container.py -v
```
**期待結果:** All passed

---

## 付録: 代替手段（ステップ3でBを選択した場合）

### mypy設定でpromptsを完全除外
```toml
# pyproject.toml に追加
[[tool.mypy.overrides]]
module = "prompts.*"
ignore_missing_imports = true
disallow_untyped_defs = false
```
**注意:** この方法は問題を隠すだけであり、ステップ4のリネームを推奨