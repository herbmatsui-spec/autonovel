# 物語テンション＆構造バランサー 統合利用ガイド

AutoNovel に実装された3種類の決定論的・数理最適化テンションバランサーの概要と利用方法です。
中盤の中だるみ（Sagging Middle）、構造違反、テンションの平坦化を検知し是正します。

---

## 1. 概要とアーキテクチャ

| バランサー | アプローチ | 特徴・適用シナリオ |
|---|---|---|
| **F1: DSP Tension Balancer** | 離散信号処理 (FFT / スペクトル平坦度 / インパルス応答) | 最速 (p99 < 5ms)。時系列テンション波形のみから機械的に中だるみを検知し、急激なインパルス（大打撃）を畳み込み補正。 |
| **F2: CSP/SAT Balancer** | 制約充足・最適化 (Google OR-Tools CP-SAT) | 厳密解。ミッドポイント・オールイズロスト・伏線回収・キャラ登場均等性を考慮し、未確定話や中盤破綻を「最小変更」で求解。 |
| **F3: Grammar DP Balancer** | 文脈自由文法 (CFG) + Earley構文解析 + 動的計画法 (DP) | 構造的整合性。物語構成規則に基づき部分構文解析を行い、未完了非終端記号の最小完結展開や文法書き換え規則（停滞→災厄化等）を適用。 |

---

## 2. Python API の利用方法

### F1: DSP Tension Balancer
```python
from src.narrative_balancer.dsp import DSPTensionBalancer, DSPConfig
from src.narrative_balancer.models import Beat, BeatType

balancer = DSPTensionBalancer()
beats = [Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 41)]

# 診断のみ
sags = balancer.analyze(beats)
print(f"検知された中だるみ区間: {len(sags)} 件")

# 自動補正
corrected_beats = balancer.correct(beats)
```

### F2: CSP/SAT Balancer
```python
from src.narrative_balancer.csp import CSPNarrativeBalancer, PartialPlotState
from src.narrative_balancer.models import Beat, BeatType

balancer = CSPNarrativeBalancer()

# 確定話（第1話と第40話のみ等）から全体を求解・修復
partial = PartialPlotState(
    total_episodes=40,
    confirmed_beats={
        1: Beat(episode=1, tension=4.0, beat_type=BeatType.SETUP),
        40: Beat(episode=40, tension=9.5, beat_type=BeatType.CLIMAX),
    }
)
solved_beats = balancer.balance(partial)
```

### F3: Grammar DP Balancer
```python
from src.narrative_balancer.grammar import GrammarNarrativeBalancer
from src.narrative_balancer.models import Beat, BeatType

balancer = GrammarNarrativeBalancer()
beats = [Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 41)]

# 診断とレポート生成
analysis = balancer.analyze_only(beats)
print(f"未完了非終端記号: {analysis.pending_nonterminals}, 推定コスト: {analysis.total_cost}")

# 文法書き換えとミッドポイント補正
balanced_beats = balancer.balance(beats)
```

### F0: Global Narrative Balancer (Arbitrator 統合)
```python
from src.narrative_balancer import GlobalNarrativeBalancer, PlotState, Beat

balancer = GlobalNarrativeBalancer()
beats = [Beat(episode=i, tension=3.0) for i in range(1, 41)]

# 3エンジンを並行実行し、優先度階層（Grammar > CSP > DSP）で自動調停
integrated = balancer.orchestrate(beats)
print(f"解決された競合数: {len(integrated.conflicts)}, 所要時間: {integrated.total_elapsed_ms}ms")
final_beats = integrated.balanced_beats
```

---

## 3. CLI コマンド

```bash
# 0. Global アービトレーター（推奨・3エンジン統合）
global-balance --input beats.json --output balanced.json --report report.json

# 1. DSP バランサー単体
dsp-balance --input beats.json --output corrected_dsp.json --config config/dsp_balancer.yaml

# 2. CSP バランサー単体
csp-balance --state partial_state.json --output solved_csp.json --config config/csp_balancer.yaml

# 3. Grammar バランサー単体
grammar-balance --input beats.json --output balanced_grammar.json --dot tree.dot --md report.md
```

