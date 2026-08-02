# 詳細実装計画書（48ステップ）

## プロジェクト概要
このプロジェクトは「覇権小説エンジン」と呼ばれる日本語小説生成システムです。以下の主要コンポーネントで構成されています：
- プロンプト管理システム（prompts/）
- ドメインモデル（src/domain/）
- エージェントシステム（src/agents/）
- サービス層（src/services/）
- Streamlit UI（streamlit_app/）

## 現状の課題
1. **kernelsパッケージが存在しない** - wiring_configで参照されているが実装されていない
2. **Streamlit UIコンポーネントが不足** - icons.py, nsfw_disclaimer.py, ui_components.py, widgets.py
3. **Lint/Typeエラー** - ruffで512件、mypyで597件のエラー
4. **テスト失敗** - 非同期フィクスチャ問題、インポートエラー

---

## Phase 1: 不足モジュールの作成（ステップ 1-12）

### Step 1: kernelsパッケージの作成
```
mkdir -p src/kernels
touch src/kernels/__init__.py
```
- **目的**: wiring_configで参照されているkernelsパッケージを作成
- **内容**: パッケージ初期化ファイルのみ

### Step 2: kernels/__init__.py の実装
```python
"""
kernels package - 覇権小説生成エンジンの核となる機能群
"""
__version__ = "1.0.0"
```
- **目的**: パッケージのエントリポイントとバージョン定義

### Step 3: streamlit_app/ui/icons.py の作成
```python
# UIアイコン（絵文字）定義
ICON_PLANNING = "🧙"
ICON_WRITING = "✍️"
ICON_ANALYTICS = "📈"
ICON_AUDIT = "⚖️"
ICON_MARKETING = "📢"
ICON_MONITOR = "📡"
ICON_SETTINGS = "⚙️"
ICON_HELP = "❓"
ICON_WARNING = "⚠️"
ICON_SUCCESS = "✅"
ICON_ERROR = "🚨"
ICON_INFO = "ℹ️"
ICON_LIGHTBULB = "💡"
ICON_STAR = "✨"
ICON_RECYCLE = "🔄"
ICON_STOP = "🛑"
ICON_SEARCH = "🔍"
```
- **目的**: landing.pyで使用されているアイコン定数を定義

### Step 4: streamlit_app/ui/components/nsfw_disclaimer.py の作成
```python
import streamlit as st
from streamlit_app.state import UIStateStore

@st.dialog("⚠️ NSFWコンテンツに関する同意確認", width="medium")
def _show_nsfw_dialog(store):
    st.warning("このモードでは、成人向けの官能的な描写を含むコンテンツが生成されます。")
    st.markdown("""
    **利用規約および注意事項:**
    1. **年齢制限**: 18歳未満の方の利用を禁止します。
    2. **自己責任**: 生成される内容はAIによる自動生成であり、倫理的・法的な判断はユーザー自身の責任で行ってください。
    3. **表現の強度**: 設定により描写の強度が変動します。不快に感じた場合は直ちにNSFWモードをOFFにしてください。
    上記内容に同意し、官能特化型機能を利用しますか？
    """)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("同意して有効にする", type="primary"):
            store.set_form_data("nsfw_consented", True)
            st.rerun()
    with col2:
        if st.button("同意せず戻る"):
            st.rerun()

def render_nsfw_disclaimer() -> bool:
    store = UIStateStore()
    if store.get_form_data("nsfw_consented", False):
        return True
    _show_nsfw_dialog(store)
    return False
```
- **目的**: writing_params.pyでインポートされているNSFW同意ダイアログを実装

### Step 5: streamlit_app/ui/components/__init__.py の作成
```python
# components package
```
- **目的**: componentsディレクトリをPythonパッケージ化

### Step 6: streamlit_app/ui_components.py の作成
- backup/streamlit_app_backup/ui_components.py からコピー
- **目的**: UI共通コンポーネント（進捗表示、ダッシュボード、ログ表示等）を実装

### Step 7: streamlit_app/ui/components/widgets.py の作成
- backup/streamlit_app_backup/ui/components/widgets.py からコピー
- 依存するstreamlit_app.progress, streamlit_app.event_bus はモックまたは簡易実装で代替
- **目的**: 共通UIウィジェット（ボタン、ヘッダー、進捗フラグメント）を実装

### Step 8: tests/mocks/mock_streamlit.py に dialog メソッド追加
```python
def dialog(self, title, width="medium"):
    def decorator(func):
        return func
    return decorator
```
- **目的**: テスト用モックにdialogデコレータを追加

### Step 9: config/settings.py の Pydantic v2 対応
```python
# 変更前
class Settings(BaseSettings):
    class Config:
        env_file = ".env"

# 変更後
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
```
- **目的**: Pydantic v2 非推奨警告の解消

### Step 10: src/models/report.py の Pydantic v2 対応
- ProductionReport クラスを同様に修正
- **目的**: Pydantic v2 非推奨警告の解消

### Step 11: pyproject.toml の mypy 設定見直し
- ignore_missing_imports = true を適切なモジュールに限定
- **目的**: 型チェックの精度向上

### Step 12: 不足している __init__.py ファイルの作成
```bash
find src -type d ! -name "__pycache__" -exec touch {}/__init__.py \;
find streamlit_app -type d ! -name "__pycache__" -exec touch {}/__init__.py \;
```
- **目的**: すべてのディレクトリをPythonパッケージとして認識可能にする

---

## Phase 2: インフラ・設定の修正（ステップ 13-18）

### Step 13: src/core/container/infra.py の wiring_config 修正
```python
wiring_config = containers.WiringConfiguration(packages=["src", "src.kernels", "prompts"])
```
- **目的**: kernelsパッケージを正しいパスで参照

### Step 14: src/engine_service.py に get_instance メソッド追加
```python
_instance = None

@classmethod
def get_instance(cls, api_key: Optional[str] = None):
    if cls._instance is None:
        cls._instance = cls(api_key)
    return cls._instance
```
- **目的**: テストでモック化している get_instance メソッドを実装

### Step 15: alembic マイグレーションファイルの修正
- `src/backend/alembic/versions/c2d671bd984b_add_multi_dimensional_tension_fields.py`
- drop_constraint の引数を文字列に修正
- **目的**: マイグレーション実行時のエラー解消

### Step 16: src/services/writing_services_utils.py の戻り値修正
- None を返す箇所を適切な dict に修正
- **目的**: mypy エラー解消

### Step 17: src/services/safe_replace.py の型注釈修正
- Pattern[str] 型の変数に None を代入しないよう修正
- **目的**: mypy エラー解消

### Step 18: src/backend/protocols.py のデフォルト引数修正
```python
# 変更前
genre: str = None

# 変更後
genre: Optional[str] = None
```
- **目的**: mypy の no_implicit_optional エラー解消

---

## Phase 3: Lint/Type エラーの修正（ステップ 19-30）

### Step 19: ruff --fix で自動修正可能なエラーを解消
```bash
cd /workspaces/autonovel && python -m ruff check src/ --fix
```
- **目的**: 250件の自動修正可能エラーを解消

### Step 20: 未使用インポートの削除 (F401)
- ClassVar, Optional, Any, Dict 等の未使用インポートを削除
- **対象ファイル**: state_validator.py, shared/utils/__init__.py 等

### Step 21: 未使用変数の削除 (F841)
- retry_prompt, book, corpus_tokens, changes_obj, cfg 等の未使用変数を削除または使用
- **対象ファイル**: plot.py, writing.py, vector_store.py, writing_services.py 等

### Step 22: 複雑度の高い関数の分割 (C901)
- rebuild_hegemony_plot (複雑度29→15以下)
- _apply_audit_loop (複雑度19→15以下)
- generate_episodes_pipeline (複雑度23→15以下)
- execute_generation_loop (複雑度18→15以下)
- **手法**: ヘルパー関数への分離、早期リターンの活用

### Step 23: 未定義名の修正 (F821)
- PlotIntegrityMonitor のインポート追加または実装
- **対象**: planning_rebuild_mixin.py

### Step 24: インポート順序の整理 (I001)
```bash
cd /workspaces/autonovel && python -m ruff check src/ --select I --fix
```
- **目的**: インポートブロックのソート

### Step 25: ファイル末尾の改行追加 (W292)
- state_validator.py, circuit_breaker.py 等
- **目的**: PEP 8 準拠

### Step 26: mypy エラーの段階的解消
- **優先度高**: 戻り値型不一致、属性未定義、インデックス型エラー
- **優先度中**: 未使用インポート、Optional型の明示
- **優先度低**: 複雑なジェネリクス、プロトコルの分散

### Step 27: src/services/episode_context.py の型修正
- 辞書型を int に代入している箇所を修正
- **目的**: mypy エラー解消

### Step 28: src/engine/prompts/erotic_specialist.py の型修正
- 型への代入、Callable への None 代入を修正
- **目的**: mypy エラー解消

### Step 29: src/core/observability.py のオーバーライド修正
- Liskov substitution principle 違反を修正
- **目的**: mypy エラー解消

### Step 30: src/services/tracing_service.py の型修正
- Token[str | None] への None 代入を修正
- **目的**: mypy エラー解消

---

## Phase 4: 実行時エラー・テスト修正（ステップ 31-36）

### Step 31: 循環インポートの解消
- `src/engine_service.py` と `src/services/llm_service.py` の相互インポートを解消
- **手法**: 遅延インポート、インターフェース分離

### Step 32: 非同期フィクスチャ問題の解決
- tests/unit/test_async_executor.py のインデント修正
- conftest.py に async フィクスチャ定義を追加
- **目的**: pytest-asyncio 対応

### Step 33: archive/ 以下の構文エラー除外
- pytest.ini に `norecursedirs = archive .kilo backup` を追加
- **目的**: テスト収集時の構文エラー防止

### Step 34: streamlit_app/api_client.py のテスト修正
- テスト側の fake_request シグネチャを実装に合わせて修正
- **目的**: test_api_client_http_semantics.py 通過

### Step 35: EngineService.get_instance モックの修正
- test_app_integration.py で実際のクラスメソッドをモック
- **手法**: `monkeypatch.setattr(EngineService, "get_instance", lambda api_key=None: engine_service_mock)`

### Step 36: integration テストの安定化
- 実DB/Redisが必要なテストは @pytest.mark.integration でマーク
- CI ではスキップ、ローカルでは実行可能に

---

## Phase 5: コア機能の実装・改善（ステップ 37-42）

### Step 37: kernels パッケージの最小実装
```python
# src/kernels/base.py
class KernelBase:
    pass

class KernelState:
    pass
```
- **目的**: 依存しているモジュールがインポート可能になる最小限の実装

### Step 38: kernels/connection_kernel.py の実装
```python
from src.kernels.base import KernelBase
class ConnectionKernel(KernelBase):
    pass
```
- **目的**: test_connection_kernel.py のインポート解決

### Step 39: kernels/graph.py の最小実装
- NarrativeState, NarrativeStateGraph, NarrativeStateManager クラス
- **目的**: test_narrative_engineering.py, test_commercial_roles.py のインポート解決

### Step 40: 依存性注入コンテナの完全動作確認
```bash
python -c "from src.core.container.infra import InfraContainer; c = InfraContainer(); print('OK')"
```
- **目的**: 依存性注入の配線が正しく動作することを確認

### Step 41: 全ユニットテストの実行・修正
```bash
python -m pytest tests/unit/ -v --tb=short
```
- **目標**: 90%以上のテスト通過

### Step 42: 統合テストの実行・修正
```bash
python -m pytest tests/integration/ -v --tb=short -k "not integration"
```
- **目標**: 主要統合テスト通過

---

## Phase 6: 品質保証・ドキュメント（ステップ 43-48）

### Step 43: 事前コミットフックの設定
```yaml
# .pre-commit-config.yaml 更新
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```
- **目的**: コミット時の自動整形

### Step 44: 型チェックの CI 組み込み
```bash
# GitHub Actions / pre-commit で実行
python -m mypy src/ --strict
```
- **目標**: エラー0件

### Step 45: テストカバレッジ測定・向上
```bash
python -m pytest --cov=src --cov-report=term-missing
```
- **目標**: カバレッジ 80% 以上

### Step 46: パフォーマンスベンチマーク作成
- 主要パス（生成、監査、推敲）の実行時間測定
- ボトルネック特定と改善

### Step 47: API ドキュメント生成
```bash
pip install pdoc
pdoc -o docs/api src/
```
- **目的**: 開発者向けドキュメント整備

### Step 48: 最終動作確認・リリース準備
- 全テストスイート実行
- 手動動作確認（Streamlit アプリ起動）
- CHANGELOG.md 更新
- バージョンタグ付け

---

## 実行順序の推奨

1. **即時実行** (Step 1-12): 不足ファイル作成で実行時エラー解消
2. **同日中** (Step 13-18): 設定修正でテスト実行可能化
3. **数日以内** (Step 19-30): Lint/Type エラー解消でコード品質確保
4. **1週間以内** (Step 31-36): テスト安定化
5. **2週間以内** (Step 37-42): コア機能完成
6. **リリース前** (Step 43-48): 品質保証・ドキュメント

## 成功基準
- ✅ `python -m pytest tests/unit/` 全通過
- ✅ `python -m ruff check src/` エラー0件
- ✅ `python -m mypy src/` エラー0件
- ✅ `streamlit run streamlit_app/app.py` 正常起動
- ✅ 主要ユースケース（企画→プロット→執筆→監査→出力）がエンドツーエンドで動作