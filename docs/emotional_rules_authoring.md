# 感情変化ルールセット拡張ガイド (Week 2 Step 19)

感情状態キャッシュ Week 2 のルールエンジンにおける、新規イベントタイプ・
条件関数の追加手順とデバッグ方法を説明する。

## アーキテクチャ概要

```
プロットイベント (config/plot_events.yaml)
        ↓ parse_episode_events()
PlotEvent
        ↓ RuleEngine.process_event()
EmotionalRule (config/emotional_rules.yaml)  ← 条件関数 (src/rules/conditions.py)
        ↓ state_machine.apply_delta()
EmotionalSignal → EmotionalVector
        ↓ persist_results()
Vector (rule_engine) / Graph / Log (JSONL)
```

## 1. 新規イベントタイプ追加手順

### 1.1 Enum に値を追加

[`src/rules/plot_events.py`](../src/rules/plot_events.py) の `PlotEventType` に
新しい値を追加する:

```python
class PlotEventType(str, Enum):
    ...
    WEDDING = "wedding"  # 新規追加
```

### 1.2 ルールセット YAML にルールを追加

[`config/emotional_rules.yaml`](../config/emotional_rules.yaml) に
ルールを追加する:

```yaml
rules:
  - event_type: "wedding"
    source_role: "participant"
    target_role: "participant"
    emotion_deltas:
      affection: 0.6
      intimacy: 0.4
      tension: -0.2
    decay_per_episode: 0.05
```

### 1.3 プロットイベントファイルにイベントを追加

[`config/plot_events.yaml`](../config/plot_events.yaml) に
イベントを追加する:

```yaml
episode_17:
  - event_id: "ep17_wedding"
    event_type: "wedding"
    scene: 5
    roles:
      participant: "A"
```

## 2. 条件関数追加手順

### 2.1 関数を定義してレジストリに登録

[`src/rules/conditions.py`](../src/rules/conditions.py) に
`@condition_registry.register("名前")` でデコレートした関数を追加する:

```python
@condition_registry.register("relationship_below")
def relationship_below(ctx: PlotContext, threshold: float = 0.3) -> bool:
    """関係レベルが閾値以下か判定。"""
    return ctx.relationship_level <= threshold
```

条件関数のシグネチャは `Callable[[PlotContext], bool]`。
パラメータを取る関数は `condition_registry.create(name, **params)` で
部分適用される。

### 2.2 YAML で条件を参照

```yaml
rules:
  - event_type: "rejection"
    source_role: "confessor"
    target_role: "listener"
    emotion_deltas:
      sadness: 0.5
    condition: "relationship_below"
    condition_params:
      threshold: 0.3
```

**重要**: 文字列式は `eval` されない。必ずレジストリに登録された名前を
指定すること。未登録の名前を指定した場合は無条件適用 (常に True) に
フォールバックする (ログに警告が出力される)。

## 3. デバッグ用ログ出力方法

### 3.1 ログレベル設定

ルール適用の詳細は DEBUG レベルで出力される:

```python
import logging
logging.getLogger("src.rules.engine").setLevel(logging.DEBUG)
```

出力例:

```
DEBUG:src.rules.engine:Rule rule_0 applied: A -> B [affection] -0.600
```

### 3.2 デバッグ CLI

[`src/rules/debug_cli.py`](../src/rules/debug_cli.py) を使用する:

```bash
# 状態確認
python -m src.rules.debug_cli show-state --episode 15 --pair A B

# 因果パス確認
python -m src.rules.debug_cli show-graph-path --source A --target B

# ログ確認
python -m src.rules.debug_cli show-log --pair A B --from 10 --to 15
```

### 3.3 再計算ツール

プロット修正時は [`src/rules/watcher.py`](../src/rules/watcher.py) で
再計算する:

```bash
python -m src.rules.watcher recompute --from 14
```

## 4. 減衰の仕組み

- 各ルールは `decay_per_episode` (0.0 ~ 1.0) を持つ
- 状態マシンは各感情値に「起源ルールの decay_per_episode」を紐付ける
- エピソード境界で `value *= (1 - decay) ** 経過話数` を適用
- 例: decay=0.1 の場合、5話放置で値は 0.9^5 ≈ 0.59 倍になる

## 5. テスト

- ユニットテスト: `tests/unit/rules/`
- YAML テスト: `tests/unit/config/test_emotional_rules_yaml.py`
- 統合テスト: `tests/integration/rules/`
- リグレッション: `tests/regression/test_rule_engine_regression.py`
