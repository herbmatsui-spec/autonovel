# 感情状態キャッシュ Week 2 完了ドキュメント (Step 24)

**Week 2**: ルールエンジン＋プロット連動ベースライン生成

## 実装概要

プロットイベント定義 → 感情変化ルール適用 → ベースラインベクトル自動生成 →
Vector/Graph/Log への永続化を実現した (LLM 呼び出しなし)。

## アーキテクチャ

```
config/plot_events.yaml (プロットイベント)
        ↓ parse_episode_events() [src/rules/rule_loader.py]
PlotEvent [src/rules/plot_events.py]
        ↓ RuleEngine.process_event() [src/rules/engine.py]
EmotionalRule [src/rules/emotional_rules.py] ← 条件関数レジストリ [src/rules/conditions.py]
        ↓ EmotionalStateMachine.apply_delta() [src/rules/state_machine.py]
EmotionalSignal → EmotionalVector
        ↓ RuleEngine.persist_results()
Vector (rule_engine) / Graph [src/stores/graph_store.py] / Log [src/stores/event_log.py]
```

## 1. ルール定義・追加方法

詳細は [emotional_rules_authoring.md](emotional_rules_authoring.md) を参照。

### 基本構造 (config/emotional_rules.yaml)

```yaml
rules:
  - event_type: "betrayal"        # PlotEventType の値
    source_role: "victim"         # 感情を感じる側
    target_role: "perpetrator"    # 感情を向けられる側
    emotion_deltas:
      affection: -0.6
      tension: 0.8
    decay_per_episode: 0.1        # 1話あたりの減衰率
```

### 条件付きルール

```yaml
  - event_type: "forced_cooperation"
    source_role: "victim"
    target_role: "perpetrator"
    emotion_deltas:
      tension: 0.3
    condition: "tension_above"    # レジストリの条件名 (eval 不使用)
    condition_params:
      threshold: 0.6
```

## 2. プロットイベントファイル形式

```yaml
episode_14:
  - event_id: "ep14_betrayal"
    event_type: "betrayal"
    scene: 3                      # 同一エピソード内の順序
    roles:
      victim: "A"                 # Role の値 → キャラクター名
      perpetrator: "B"
    metadata:
      witness: "C"
      relationship_level: 0.6     # 条件評価に使用される
```

## 3. 再計算コマンド使い方

```bash
# プロット修正時の再計算 (ep14 以降)
python -m src.rules.watcher recompute --from 14

# オプション
python -m src.rules.watcher recompute --from 14 \
  --rules config/emotional_rules.yaml \
  --events config/plot_events.yaml \
  --log data/emotional_events.jsonl \
  --graph data/kuzu.db
```

## 4. Graph/Log 確認方法 (デバッグCLI)

```bash
# 感情状態確認 (エピソード時点の状態をログから再構築)
python -m src.rules.debug_cli show-state --episode 15 --pair A B

# 因果パス確認 (感情エッジの伝播経路)
python -m src.rules.debug_cli show-graph-path --source A --target B

# イベントログ確認
python -m src.rules.debug_cli show-log --pair A B --from 10 --to 15
```

## 5. Week 1 との併用時の挙動

### ネームスペース分離

| ネームスペース | 用途 | 週 |
|---|---|---|
| `pipeline` | 自動抽出 (脚本テキストから) | Week 1 |
| `rule_engine` | ベースライン (プロットイベントから) | Week 2 |
| `annotation` | 人間上書き | Week 3 |

- 両方のベクトルがそれぞれのネームスペースに保存される
- 融合は読み取り側 (Week 4) で実施
- Week 1 の `EmotionalVector`/`EmotionalSignal` データ構造をそのまま共有
- Week 1 機能への影響なし (リグレッションテストで確認済み)

### パイプライン統合

[`src/pipeline/compression_pipeline.py`](../src/pipeline/compression_pipeline.py) の
`CompressionPipeline` が両方のベクトルソースを管理する:

```python
from src.pipeline.compression_pipeline import CompressionPipeline, create_rule_engine

pipeline = CompressionPipeline(
    vector_store=store,
    rule_engine=create_rule_engine(),
)
result = pipeline.run("ep14", "脚本テキスト", episode=14)
# result["rule_engine_vector"] → True (ベースライン生成済み)
```

## 6. 実装ファイル一覧

| Step | ファイル | 内容 |
|---|---|---|
| 1 | `src/rules/plot_events.py` | PlotEventType/Role/PlotEvent |
| 2 | `src/rules/emotional_rules.py` | EmotionalRule/PlotContext |
| 3 | `config/emotional_rules.yaml` | ルールセット (8ルール) |
| 4 | `src/rules/rule_loader.py` | RuleLoader/parse_episode_events |
| 5 | `src/rules/conditions.py` | 条件関数レジストリ (4関数) |
| 6 | `config/plot_events.yaml` | プロットイベント (ep14-16) |
| 7 | `src/rules/state_machine.py` | EmotionalStateMachine |
| 8-10, 13 | `src/rules/engine.py` | RuleEngine (process_event/episode/decay/persist) |
| 11 | `src/stores/graph_store.py` | GraphStore/InMemory/Kuzu |
| 12 | `src/stores/event_log.py` | EventLogStore (JSONL) |
| 15-16 | `src/pipeline/compression_pipeline.py` | CompressionPipeline |
| 15 | `config/pipeline.yaml` | パイプライン設定 |
| 17 | `src/rules/watcher.py` | 再計算ツール |
| 19 | `docs/emotional_rules_authoring.md` | 拡張ガイド |
| 20 | `src/rules/debug_cli.py` | デバッグCLI |
| 21 | `tests/regression/test_week2_regression.py` | リグレッション |
| 22 | `.github/workflows/rule_engine.yml` | CI/CD |
| 23 | `tests/performance/test_rule_engine_perf.py` | 性能テスト |

## 7. テスト実行

```bash
# 全 Week 2 テスト
pytest tests/unit/rules/ tests/unit/config/test_emotional_rules_yaml.py \
  tests/unit/config/test_plot_events_yaml.py tests/unit/stores/test_graph_store.py \
  tests/unit/stores/test_event_log.py tests/unit/pipeline/test_rule_engine_stage.py \
  tests/integration/rules/ tests/integration/pipeline/test_dual_vector_sources.py \
  tests/regression/test_rule_engine_regression.py tests/regression/test_week2_regression.py \
  tests/performance/test_rule_engine_perf.py
```

## 8. 完了チェックリスト

- [x] 全 Step 1-24 テストパス
- [x] `config/plot_events.yaml` サンプルで 3話分ベースライン生成確認
- [x] Vector (rule_engine), Graph, Log の 3ストアに正しく書き込まれる
- [x] 減衰処理が話境界で正しく動作
- [x] リグレッションテスト 3ケース + Week1 リグレッション全パス
- [x] デバッグCLI で状態・グラフ・ログが確認できる
- [x] Week 1 機能に影響なし (併存確認済み)
