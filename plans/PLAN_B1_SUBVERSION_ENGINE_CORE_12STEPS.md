# PLAN_B1: SubversionEngine コアモデル実装（12ステップ）

**対象ファイル:** `src/models/subversion.py`（新規作成）  
**依存:** `src/models/base.py` の `BaseEngine`, `MODEL_CONFIG_DEFAULTS`  
**ゴール:** 決定論的・再現可能な「3話ごとの裏切りスケジュール」を生成・検証するエンジンを単体で動く形で実装

---

## Step 1: ファイル雛形・インポート・定数定義
**作業:** `src/models/subversion.py` を新規作成。必要インポートと `MODEL_CONFIG_DEFAULTS` 再エクスポートだけ記述。
**テスト:** `python -c "import src.models.subversion; print('import ok')"`

```python
# src/models/subversion.py
from __future__ import annotations
import hashlib
from typing import Literal
from pydantic import BaseModel, Field
from src.models.base import BaseEngine, MODEL_CONFIG_DEFAULTS
```

---

## Step 2: SubversionPattern モデル定義
**作業:** 裏切り1件分のデータ構造を定義。フィールド: `pattern_type`, `trigger_ep`, `description`, `cost`, `payoff_hint`, `setup_ep`。
**テスト:** インスタンス化して `model_dump()` が通ること確認。

```python
class SubversionPattern(BaseModel):
    pattern_type: Literal["A", "B", "C"] = Field(description="裏切りパターン種別")
    trigger_ep: int = Field(description="発火話数")
    description: str = Field(description="具体的な裏切り内容")
    cost: str = Field(description="代償・リスク・後々の伏線")
    payoff_hint: str = Field(default="", description="将来の回収ヒント")
    setup_ep: int | None = Field(default=None, description="伏線設置話数（遡及込み）")
    model_config = MODEL_CONFIG_DEFAULTS
```

---

## Step 3: SubversionEngine クラス雛形・ルーティングキー
**作業:** `BaseEngine` 継承クラスを作成。`get_routing_keys()` 実装。フィールド: `schedule`, `last_applied_ep`, `applied_patterns`, `interval`, `enabled`, `pattern_weights`。
**テスト:** `SubversionEngine().get_routing_keys()` が期待リストを返すこと。

```python
class SubversionEngine(BaseEngine):
    schedule: list[SubversionPattern] = Field(default_factory=list)
    last_applied_ep: int = Field(default=0)
    applied_patterns: list[SubversionPattern] = Field(default_factory=list)
    interval: int = Field(default=3, description="裏切り間隔（話数）")
    enabled: bool = Field(default=True)
    pattern_weights: dict[str, float] = Field(
        default_factory=lambda: {"A": 0.4, "B": 0.3, "C": 0.3}
    )

    @classmethod
    def get_routing_keys(cls) -> list[str]:
        return ["schedule", "last_applied_ep", "applied_patterns", "interval", "enabled", "pattern_weights"]
```

---

## Step 4: 重み合計正規化バリデーター
**作業:** `model_validator(mode="after")` で `pattern_weights` 合計が 1.0 ± 0.001 になるよう正規化。無効時はデフォルトにフォールバック。
**テスト:** 合計 0.9 / 1.2 / 空dict を渡して正規化されること確認。

```python
    @model_validator(mode="after")
    def _normalize_weights(self) -> "SubversionEngine":
        total = sum(self.pattern_weights.values())
        if abs(total - 1.0) > 0.001 or total == 0:
            self.pattern_weights = {"A": 0.4, "B": 0.3, "C": 0.3}
        else:
            self.pattern_weights = {k: v/total for k, v in self.pattern_weights.items()}
        return self
```

---

## Step 5: plan_schedule() 実装（決定論的シード）
**作業:** `plan_schedule(total_eps, start_ep=1)` を実装。MD5シードでパターン選択し `SubversionPattern` リストを生成・`self.schedule` に格納・返却。
**テスト:** 同一引数で2回呼び出し、全フィールド完全一致すること確認。

```python
    def plan_schedule(self, total_eps: int, start_ep: int = 1) -> list[SubversionPattern]:
        schedule = []
        for ep in range(start_ep + self.interval - 1, total_eps + 1, self.interval):
            seed = f"subversion_{ep}_{total_eps}_{self.interval}"
            hash_val = int(hashlib.md5(seed.encode()).hexdigest(), 16)
            rand = (hash_val % 100) / 100.0
            
            cum = 0.0
            selected = "A"
            for pat, weight in self.pattern_weights.items():
                cum += weight
                if rand <= cum:
                    selected = pat
                    break
            
            pattern = SubversionPattern(
                pattern_type=selected,
                trigger_ep=ep,
                description=self._generate_description(selected, ep),
                cost=self._generate_cost(selected, ep),
                payoff_hint=self._generate_payoff_hint(selected, ep),
                setup_ep=max(1, ep - 2)
            )
            schedule.append(pattern)
        self.schedule = schedule
        return schedule
```

---

## Step 6: パターン別テンプレートメソッド3種
**作業:** `_generate_description`, `_generate_cost`, `_generate_payoff_hint` を `match-case` または dict で実装。ハードコード文字列返却。
**テスト:** 各パターンA/B/Cで呼び出し、期待キーワード（"人間性"、"一族"、"第三の災厄"等）が含まれること確認。

```python
    def _generate_description(self, pat: str, ep: int) -> str:
        return {
            "A": f"第{ep}話：チート能力覚醒の代償として「人間性の一部（感情/記憶/倫理）」を永久に失う",
            "B": f"第{ep}話：追放の張本人・小悪党が、一族を守るため自ら囮となり命を散らす覚悟を見せる",
            "C": f"第{ep}話：ざまぁ完遂の瞬間、主人公と敵対者の双方を呑み込む「第三の災厄（古代兵器/外宇宙存在/概念的崩壊）」が出現",
        }[pat]

    def _generate_cost(self, pat: str, ep: int) -> str:
        return {
            "A": "能力使用ごとに人格が侵食。最終話で「誰だったか忘れる」エンドリスク",
            "B": "読者の共感ベクトルが逆転。以降、敵キャラへの感情移入が主軸に移る",
            "C": "復讐完了が無期限延期。新たな共通目的（生存/世界救済）へ強制ピボット",
        }[pat]

    def _generate_payoff_hint(self, pat: str, ep: int) -> str:
        return {
            "A": "失った人間性の欠片が、最終決戦で「鍵」になる伏線",
            "B": "悪役の遺した「遺言/アイテム/血統」が主人公の真の力を引き出す",
            "C": "第三の災厄の正体＝主人公の力の源泉（因果律ループ）",
        }[pat]
```

---

## Step 7: apply_to_arc() 実装
**作業:** `ArcBlueprint` 擬似オブジェクト（`hasattr`/`setattr` で動的フィールド追加可能）を受け取り、該当話数のパターンがあれば `arc.subversion = pat` と `arc.thematic_milestone` 更新。`last_applied_ep`, `applied_patterns` も更新。
**テスト:** モックArcで ep=3,6,9 に適用され、それ以外はスキップされること確認。

```python
    def apply_to_arc(self, arc: object, ep_num: int) -> object:
        if not self.enabled:
            return arc
        for pat in self.schedule:
            if pat.trigger_ep == ep_num:
                if not hasattr(arc, "subversion"):
                    arc.subversion = pat
                arc.thematic_milestone = f"【裏切り-{pat.pattern_type}】{pat.description}"
                self.last_applied_ep = ep_num
                self.applied_patterns.append(pat)
                break
        return arc
```

---

## Step 8: apply_to_beat() 実装
**作業:** `EpisodeBeat` 擬似オブジェクトを受け取り、`mission`, `visual_scene_focus`, `tension_target`（+0.3 上限1.0）を更新。
**テスト:** モックBeatで tension_target が 0.7→1.0, 0.9→1.0 にクリップされること確認。

```python
    def apply_to_beat(self, beat: object, ep_num: int) -> object:
        if not self.enabled:
            return beat
        for pat in self.schedule:
            if pat.trigger_ep == ep_num:
                beat.mission = f"【裏切り-{pat.pattern_type}】{pat.description}"
                beat.visual_scene_focus = f"代償の可視化：{pat.cost}"
                beat.tension_target = min(1.0, getattr(beat, "tension_target", 0.5) + 0.3)
                break
        return beat
```

---

## Step 9: validate_coherence() 実装
**作業:** 重複発火チェック、間隔チェック、終盤5話以内の回収ヒント警告をリストで返却。
**テスト:** 意図的に重複/間隔不足/終盤ヒントを含むスケジュールを作り、各警告が出ること確認。

```python
    def validate_coherence(self, total_eps: int) -> list[str]:
        errors = []
        eps = [p.trigger_ep for p in self.schedule]
        if len(eps) != len(set(eps)):
            errors.append("重複発火話数あり")
        for i in range(1, len(eps)):
            if eps[i] - eps[i-1] < self.interval:
                errors.append(f"間隔不足: {eps[i-1]}話→{eps[i]}話")
        for pat in self.schedule:
            if pat.payoff_hint and pat.trigger_ep > total_eps - 5:
                errors.append(f"第{pat.trigger_ep}話の回収ヒントが終盤すぎる（残り{total_eps - pat.trigger_ep}話）")
        return errors
```

---

## Step 10: 単体テストファイル作成
**作業:** `tests/test_subversion_engine.py` 作成。pytest形式で以下をカバー：
1. `plan_schedule` 再現性（同一入力→同一出力）
2. 重み正規化
3. `apply_to_arc` / `apply_to_beat` 側効果
4. `validate_coherence` 各警告
5. `enabled=False` で無効化
**テスト:** `pytest tests/test_subversion_engine.py -v` 全パス

```python
# tests/test_subversion_engine.py
import pytest
from src.models.subversion import SubversionEngine, SubversionPattern

class TestSubversionEngine:
    def test_plan_schedule_deterministic(self):
        e1 = SubversionEngine(interval=3)
        e1.plan_schedule(12)
        e2 = SubversionEngine(interval=3)
        e2.plan_schedule(12)
        assert [p.model_dump() for p in e1.schedule] == [p.model_dump() for p in e2.schedule]

    def test_weight_normalization(self):
        e = SubversionEngine(pattern_weights={"A": 0.9, "B": 0.2})
        assert abs(sum(e.pattern_weights.values()) - 1.0) < 0.001

    def test_apply_to_arc(self):
        class MockArc: pass
        e = SubversionEngine(interval=3)
        e.plan_schedule(9)
        arc = MockArc()
        e.apply_to_arc(arc, 3)
        assert hasattr(arc, "subversion")
        assert arc.subversion.pattern_type in {"A","B","C"}
        # ep=4 はスキップ
        e.apply_to_arc(arc, 4)
        assert arc.subversion.trigger_ep == 3

    def test_apply_to_beat_tension_clip(self):
        class MockBeat:
            tension_target = 0.9
        e = SubversionEngine(interval=3)
        e.plan_schedule(6)
        beat = MockBeat()
        e.apply_to_beat(beat, 3)
        assert beat.tension_target == 1.0

    def test_validate_coherence(self):
        e = SubversionEngine(interval=3)
        e.schedule = [
            SubversionPattern(pattern_type="A", trigger_ep=3, description="d", cost="c", payoff_hint="h"),
            SubversionPattern(pattern_type="B", trigger_ep=3, description="d", cost="c", payoff_hint="h"),  # 重複
            SubversionPattern(pattern_type="C", trigger_ep=5, description="d", cost="c", payoff_hint="h"),  # 間隔不足
            SubversionPattern(pattern_type="A", trigger_ep=38, description="d", cost="c", payoff_hint="h"), # 終盤
        ]
        errors = e.validate_coherence(40)
        assert "重複発火話数あり" in errors
        assert any("間隔不足" in e for e in errors)
        assert any("終盤すぎる" in e for e in errors)

    def test_disabled(self):
        e = SubversionEngine(enabled=False, interval=3)
        e.plan_schedule(6)
        class Mock: pass
        assert e.apply_to_arc(Mock(), 3) is not None  # 何もしない
```

---

## Step 11: 型ヒント・ForwardRef 解決
**作業:** `apply_to_arc` / `apply_to_beat` の引数型を `Any` または `Protocol` に緩和し、循環インポート回避。`from __future__ import annotations` 既にあるので文字列アノテーションでも可。
**テスト:** `mypy src/models/subversion.py` エラーなし。

---

## Step 12: 統合動作確認スクリプト
**作業:** `scripts/verify_subversion.py` 作成。40話分スケジュール生成→表示→検証まで一発実行。
**テスト:** `python scripts/verify_subversion.py` で警告なし・全話数表示されること。

```python
# scripts/verify_subversion.py
from src.models.subversion import SubversionEngine

engine = SubversionEngine(interval=3)
engine.plan_schedule(40)
for p in engine.schedule:
    print(f"Ep{p.trigger_ep:2d} [{p.pattern_type}] {p.description}")
    print(f"    Cost: {p.cost}")
    print(f"    Payoff: {p.payoff_hint}")
print("\nValidation:", engine.validate_coherence(40))
```

---

## 完了基準
- [ ] `src/models/subversion.py` 作成完了
- [ ] `tests/test_subversion_engine.py` 全テストパス
- [ ] `mypy` / `ruff` クリーン
- [ ] `scripts/verify_subversion.py` 正常出力