# リファクタリング 残タスク 詳細実装計画書

## 前提条件

- 作業ディレクトリ: `I:\R15\cR15`
- Python 3.11+
- Streamlit アプリケーション

---

## Step 1: src/state_manager.py の削除

**目的:** 使用されていないラッパーを削除

**コマンド:**
```powershell
Remove-Item -LiteralPath "I:\R15\cR15\src\state_manager.py" -Force
```

**検証:**
```powershell
Test-Path -LiteralPath "I:\R15\cR15\src\state_manager.py"
# False が出力されれば削除成功
```

---

## Step 2: src/shared/utils/ 使用状況確認

**目的:** backend/background.py が src.shared.utils を使用しているか確認

**コマンド:**
```bash
grep -r "from src.shared.utils import" I:\R15\cR15\src
```

**期待結果:**
- `src/backend/background.py` からのみ参照されている
- 出力例: `src/backend/background.py:10: from src.shared.utils import StatusReporter, TokenUsageTracker, estimate_tokens`

**判断:**
- 出力がある場合 → `src/shared/utils/__init__.py` はビジネスロジック層に必要なため維持
- 出力がない場合 → `src/shared/utils/` ディレクトリを削除して `streamlit_app/utils/__init__.py` のみを使用

---

## Step 3: src/shared/utils/profiler.py 使用確認

**目的:** profiler が使用されているか確認

**コマンド:**
```bash
grep -r "from src.shared.utils.profiler import\|import src.shared.utils.profiler" I:\R15\cR15\src
```

**判断:**
- 出力がある場合 → 維持
- 出力がない場合 → 削除して OK

---

## Step 4: src/api/client.py と streamlit_app/api_client.py の比較

**目的:** 重複があるか確認し、アーキテクチャを整理

**確認事項:**

1. `src/api/client.py` を読む
2. `streamlit_app/api_client.py` を読む
3. 重複がある場合:
   - `src/api/client.py` を正とする (ビジネスロジック)
   - `streamlit_app/api_client.py` から `src/api/client` をインポートする
4. 重複がない場合:
   - 各ファイルが別の目的を果たしているか確認

**一般的な判断基準:**
- `src/api/client.py` → バックエンドAPIへの低レベルHTTPクライアント
- `streamlit_app/api_client.py` → Streamlit UI がバックエンドと通信するための高层クライアント

---

## Step 5: テスト実行

**目的:** 既存テストがパスすることを確認

**コマンド:**
```bash
cd I:\R15\cR15
pytest tests/ -v --tb=short
```

**期待結果:**
- テストがパスする (または、修正が必要なテストが明確になる)

**エラーが出た場合:**
- import エラー → インポートパスが正しいか確認
- テスト失敗 → テストコードを修正 (src.* のインポート先が変更になったため)

---

## Step 6: ドキュメント更新

### 6-1: README.md の確認と更新

**確認:**
```bash
cat I:\R15\cR15\README.md
```

**更新の必要性:**
- 「src/はラッパー」という記述があれば削除
- 「streamlit_app/がUI層で実装を持つ」という記述を追加
- アーキテクチャ図があれば更新

### 6-2: docs/ 内のドキュメント確認

**対象ファイル:**
- `docs/di_architecture.md`
- `docs/ui_partitioning_policy.md`
- `docs/ui_dependency_map.md`
- `docs/architecture_refactoring_plan.md`

**更新:**
- ラッパー層の削除を反映
- src/ がビジネスロジック層のみであることを明記
- streamlit_app/ がUI層であることを明記

---

## Step 7: インテグレーションテスト新規作成

**ファイル:** `tests/integration/test_ui_backend_communication.py`

**最小実装:**
```python
"""
UI とバックエンドAPIの通信テスト
"""
import pytest
from unittest.mock import MagicMock, patch

def test_ui_can_import_progress():
    """streamlit_app.progress が正しくインポートできるか"""
    from streamlit_app.progress import run_in_background, ProgressStateProxy
    assert run_in_background is not None
    assert ProgressStateProxy is not None

def test_ui_can_import_state():
    """streamlit_app.state が正しくインポートできるか"""
    from streamlit_app.state import UIStateStore, get_session
    assert UIStateStore is not None
    assert get_session is not None

def test_ui_can_import_proxy():
    """streamlit_app.proxy が正しくインポートできるか"""
    from streamlit_app.proxy import UltimateHegemonyEngineProxy
    assert UltimateHegemonyEngineProxy is not None

def test_ui_can_import_actions():
    """streamlit_app.actions が正しくインポートできるか"""
    from streamlit_app.actions import generate_plan, write_episode
    assert generate_plan is not None
    assert write_episode is not None

@patch('streamlit_app.api_client.get_task_status')
def test_progress_state_proxy_refresh(mock_get_status):
    """ProgressStateProxy.refresh() が正しく動作するか"""
    mock_get_status.return_value = {
        "is_running": True,
        "current_step": 5,
        "total_steps": 10,
        "message": "処理中",
        "sub_message": "Step 5",
        "logs": [],
        "error": None
    }
    from streamlit_app.progress import ProgressStateProxy
    proxy = ProgressStateProxy(task_id="test-task-123")
    proxy.refresh()
    assert proxy.is_running == True
    assert proxy.current_step == 5
    assert proxy.total_steps == 10
```

**実行コマンド:**
```bash
cd I:\R15\cR15
pytest tests/integration/test_ui_backend_communication.py -v
```

---

## Step 8: 手動検証

### 8-1: streamlit_app アプリケーション起動確認

**コマンド:**
```bash
cd I:\R15\cR15
streamlit run streamlit_app/app.py --server.headless true
```

**確認ポイント:**
- [ ] アプリケーションがエラーなしで起動する
- [ ] ブラウザで http://localhost:8501 にアクセスできる
- [ ] サイドバーに API キー入力が表示される

### 8-2: src.progress → streamlit_app.progress 切り替え確認

**確認方法:**

1. `streamlit_app/progress.py` の `run_in_background` 関数を確認
   - `from src.state import get_session` → `from streamlit_app.state import get_session` に変更済み

2. 以下の grep で確認:
   ```bash
   grep -r "from src.progress import\|from src.state import" I:\R15\cR15\streamlit_app
   ```
   - 出力がないこと (全て streamlit_app を参照しているべき)

### 8-3: run_in_background の動作確認

**確認方法:**

1. `streamlit_app/progress.py` を読む
2. `WORKFLOW_API_MAP` が正しく定義されているか確認
3. `api_client.get_task_status` が正しく呼び出されるか確認

---

## Step 9: src/shared/utils/ の最終確認と削除 (条件付き)

### 条件付き削除コマンド:

**Step 2 で出力がなかった場合:**
```bash
# src/shared/utils/ を削除 (streamlit_app/utils/ を使用するため)
Remove-Item -LiteralPath "I:\R15\cR15\src\shared\utils\__init__.py" -Force
Remove-Item -LiteralPath "I:\R15\cR15\src\shared\utils\profiler.py" -Force

# shared/utils ディレクトリを削除
Remove-Item -LiteralPath "I:\R15\cR15\src\shared\utils" -Recurse -Force
```

**Step 2 で出力があった場合 (backend/background.py が使用):**
- 削除しない
- `src/shared/utils/__init__.py` を維持

### 削除後の backend/background.py 修正 (必要な場合)

もし削除して `src/backend/background.py` が壊れた場合:
```python
# src/backend/background.py の先頭に追加
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "streamlit_app"))
from utils import StatusReporter, TokenUsageTracker, estimate_tokens
```

---

## Step 10: 最終検証

### Python インポート確認

```bash
cd I:\R15\cR15
python -c "
import streamlit_app.state
import streamlit_app.progress
import streamlit_app.proxy
import streamlit_app.actions
import streamlit_app.ui_components
print('All streamlit_app imports OK')
"
```

### src ビジネスロジック確認

```bash
cd I:\R15\cR15
python -c "
import src.engine_service
import src.agents
import src.models
import src.services
print('All src business logic imports OK')
"
```

---

## 完了条件チェックリスト

- [ ] `src/state_manager.py` が削除されている
- [ ] `src/shared/utils/profiler.py` が使用されていない場合削除されている
- [ ] テストがパスする
- [ ] README.md が更新されている
- [ ] docs/ が更新されている
- [ ] インテグレーションテストが追加されている
- [ ] streamlit_app/app.py が起動する
- [ ] run_in_background が正しく動作する
- [ ] Python インポートが全て成功する

---

## 次のAIへの指示

1. この план の `Step 1` から順番に実行してください
2. 各 Step を完了するたびに、完了報告をしてください
3. 問題が発生した場合は、問題を報告して次の Step を続けてください
4. すべての Step を完了したら、`完了条件チェックリスト` をチェックオフしてください