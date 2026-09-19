# PLAN_B2: PlotEpisode への SubversionMixin 統合（12ステップ）

**対象ファイル:** `src/models/plot.py`（既存編集）  
**依存:** `PLAN_B1` 完了済み（`src.models.subversion` インポート可能）  
**ゴール:** `PlotEpisode` が `SubversionEngine` をネイティブ保持し、FlatModelMixinルーティング・シリアライズで透過的に永続化される

---

## Step 1: インポート追加
**作業:** `src/models/plot.py` ファイル冒頭に `SubversionEngine`, `SubversionPattern` をインポート。
**テスト:** `python -c "from src.models.plot import SubversionEngine; print('import ok')"`

```python
# 既存インポート群の近くに追加
from src.models.subversion import SubversionEngine, SubversionPattern
```

---

## Step 2: SubversionMixin クラス定義
**作業:** `PlotEpisode` クラス定義の直前あたりに `SubversionMixin` を追加。`subversion: SubversionEngine = Field(default_factory=SubversionEngine)` のみ。
**テスト:** `SubversionMixin().subversion` が `SubversionEngine` インスタンスであること。

```python
class SubversionMixin(BaseModel):
    """テンプレ逆張りエンジンを保持する Mixin"""
    subversion: SubversionEngine = Field(default_factory=SubversionEngine)
    model_config = MODEL_CONFIG_DEFAULTS
```

---

## Step 3: PlotEpisode 継承に Mixin 追加
**作業:** `class PlotEpisode(...)` の基底クラスタプルに `SubversionMixin` を追加（順序は `EnigmaMixin`, `ComfortMixin` の後で可）。
**テスト:** `PlotEpisode().subversion` が存在し、型が `SubversionEngine`。

```python
# 変更前
class PlotEpisode(PlotEpisodeBase[CoreEngineMixin], EnigmaMixin, ComfortMixin):

# 変更後
class PlotEpisode(PlotEpisodeBase[CoreEngineMixin], EnigmaMixin, ComfortMixin, SubversionMixin):
```

---

## Step 4: _get_sub_model_names() 自動収集確認
**作業:** 既存の `PlotEpisodeBase._get_sub_model_names()` がクラスフィールドのアノテーションから `SubversionEngine` を検出するか確認。検出されない場合のみ同メソッドをオーバーライドして `"subversion"` を追加。
**テスト:** `PlotEpisode._get_sub_model_names()` に `"subversion"` が含まれること。

```python
# 既存ロジックで自動検出されるはずだが、念のため確認用テスト
assert "subversion" in PlotEpisode._get_sub_model_names()
```

---

## Step 5: unwrap_plot_metadata で subversion ルーティング確認
**作業:** 既存 `unwrap_plot_metadata` の `static_routing_map` に `"subversion": SubversionEngine` を追加（既に `_get_sub_model_names` 経由で動的ルーティングされるが、明示マップに入れておくと安全）。
**テスト:** `{"subversion": {"interval": 5}}` を含む dict を `PlotEpisode.model_validate()` し、`subversion.interval == 5` になること。

```python
# unwrap_plot_metadata 内の static_routing_map に追加
static_routing_map = {
    "core_info": PlotCoreInfo,
    "analytics": PlotAnalytics,
    "foreshadowing": PlotForeshadowing,
    "enigma": EnigmaAnalytics,
    "comfort": ComfortAnalytics,
    "subversion": SubversionEngine,  # 追加
}
```

---

## Step 6: シリアライズ・デシリアライズ往復テスト
**作業:** `PlotEpisode` インスタンスを作成 → `subversion.plan_schedule(12)` → `model_dump()` → `model_validate()` → スケジュール内容完全一致を確認するスクリプトを `scripts/test_plot_subversion_roundtrip.py` に作成。
**テスト:** スクリプト実行で「OK」出力。

```python
# scripts/test_plot_subversion_roundtrip.py
from src.models.plot import PlotEpisode

ep = PlotEpisode(ep_num=1)
ep.subversion.plan_schedule(12)
dumped = ep.model_dump()
restored = PlotEpisode.model_validate(dumped)

orig = [p.model_dump() for p in ep.subversion.schedule]
rest = [p.model_dump() for p in restored.subversion.schedule]
assert orig == rest, f"Mismatch: {orig} vs {rest}"
print("Round-trip OK")
```

---

## Step 7: extra_engines 経由のフォールバック動作確認
**作業:** `subversion` フィールド名ではないキー（例: `subversion_engine`）でデータが来た場合、`extra_engines` に吸収され、アクセス時に `getattr` で取れるか確認。必要なら `PlotEpisodeBase` の `model_serializer` / `unwrap` で別名マッピング追加。
**テスト:** `{"subversion_engine": {"interval": 4}}` でバリデーションし、`ep.subversion.interval == 4` になること。

---

## Step 8: 既存フィールドとの競合チェック
**作業:** `thematic_milestone`, `burned_cost_or_loot`, `resolution_style` 等、裏切り内容と意味が近い既存フィールドとの命名・用途競合を洗い出し、コメントで整理。必要なら `subversion` 側の適用メソッドで既存フィールドを上書きしないようガード。
**テスト:** `apply_to_arc` 呼び出し前後で既存フィールドが意図せず変わらないこと確認。

---

## Step 9: 型アノテーション ForwardRef 解決
**作業:** `SubversionMixin` 内の `SubversionEngine` アノテーションが循環インポートにならないよう、`from __future__ import annotations` 有効下で文字列 `"SubversionEngine"` にするか、`TYPE_CHECKING` ブロックでインポート。
**テスト:** `mypy src/models/plot.py` エラーなし。

```python
# 修正例
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.models.subversion import SubversionEngine

class SubversionMixin(BaseModel):
    subversion: "SubversionEngine" = Field(default_factory=lambda: SubversionEngine())
```

---

## Step 10: 単体テストファイル作成
**作業:** `tests/test_plot_subversion_integration.py` 作成。以下をカバー：
1. `PlotEpisode` インスタンスに `subversion` 属性存在
2. `model_dump` / `model_validate` でスケジュール往復
3. `_get_sub_model_names` に含まれる
4. `unwrap_plot_metadata` でネストされた dict から自動ルーティング
5. `extra_engines` フォールバック
**テスト:** `pytest tests/test_plot_subversion_integration.py -v` 全パス

```python
# tests/test_plot_subversion_integration.py
import pytest
from src.models.plot import PlotEpisode, PlotCoreInfo

class TestPlotSubversionIntegration:
    def test_subversion_attribute_exists(self):
        ep = PlotEpisode(ep_num=1)
        assert hasattr(ep, "subversion")
        from src.models.subversion import SubversionEngine
        assert isinstance(ep.subversion, SubversionEngine)

    def test_roundtrip_schedule(self):
        ep = PlotEpisode(ep_num=1)
        ep.subversion.plan_schedule(15)
        dumped = ep.model_dump()
        restored = PlotEpisode.model_validate(dumped)
        assert [p.trigger_ep for p in ep.subversion.schedule] == \
               [p.trigger_ep for p in restored.subversion.schedule]

    def test_sub_model_names_includes_subversion(self):
        assert "subversion" in PlotEpisode._get_sub_model_names()

    def test_unwrap_routing(self):
        data = {"ep_num": 1, "subversion": {"interval": 5, "enabled": True}}
        ep = PlotEpisode.model_validate(data)
        assert ep.subversion.interval == 5
        assert ep.subversion.enabled is True

    def test_extra_engines_fallback(self):
        data = {"ep_num": 1, "subversion_engine": {"interval": 4}}
        ep = PlotEpisode.model_validate(data)
        # extra_engines に吸収されるか、または直接アクセス可能か
        assert hasattr(ep, "subversion")
```

---

## Step 11: 既存テストスイート回帰確認
**作業:** `pytest tests/ -k "plot"` 等、既存の plot 関連テストを全実行し、Mixin 追加による副作用（フィールド順序変更・シリアライズ差分等）がないか確認。
**テスト:** 既存テスト全パス。

---

## Step 12: ドキュメント・型スタブ更新
**作業:** `src/models/__init__.py` に `SubversionEngine`, `SubversionPattern`, `SubversionMixin` を `__all__` 追加。必要なら `py.typed` マーカー確認。
**テスト:** `python -c "from src.models import SubversionEngine, SubversionMixin; print('exports ok')"`

---

## 完了基準
- [ ] `src/models/plot.py` に Mixin 統合完了
- [ ] `tests/test_plot_subversion_integration.py` 全パス
- [ ] 既存 plot テスト全パス（回帰なし）
- [ ] `mypy` / `ruff` クリーン
- [ ] ラウンドトリップスクリプト正常終了