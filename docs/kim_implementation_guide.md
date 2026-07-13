# カーネル間相互作用行列 (Kernel Interaction Matrix: KIM) 実装ドキュメント

## 1. 概要
KIMは、物語を構成する4つの主要カーネル（共鳴、覇権、葛藤、静謐）が互いにどのように影響し合い、状態を遷移させるかを定義する数学的フレームワークです。単なる閾値判定ではなく、行列演算を用いることで、「覇権が強まると共鳴が抑制されるが、ある一点で崩壊すると共鳴が爆発的に高まる」といった、複雑で人間らしいドラマチックな弧（アーク）を自動生成することを目的としています。

## 2. 数学的モデル
### 2.1 状態ベクトル
各カーネルの強度を $0$ から $100$ の値で持つベクトル $\mathbf{S}$ として定義します。
$$\mathbf{S} = [s_{res}, s_{heg}, s_{con}, s_{ser}]^T$$

### 2.2 状態遷移方程式
次ステップの状態 $\mathbf{S}_{t+1}$ は以下の式で決定されます。
$$\mathbf{S}_{t+1} = \text{clamp}(\mathbf{S}_t \cdot \text{decay} + \mathbf{M} \mathbf{S}_t + \mathbf{I}_t, 0, 100)$$

- $\text{decay}$: 時間経過による自然減衰率（`InteractionConfig.decay_rate`）
- $\mathbf{M}$: 相互作用行列。$M_{ij}$ はカーネル $j$ がカーネル $i$ に与える影響係数。
- $\mathbf{I}_t$: 外部からの衝撃（シーン内の具体的なイベントによる増減量）。

## 3. 実装構造
### 3.1 主要コンポーネント
- `InteractionManager`: 行列演算と状態更新のコアロジックを担う。
- `InteractionConfig`: $\mathbf{M}$ および $\text{decay}$ を `interaction_matrix.yaml` から読み込み管理する。
- `InteractionTrigger`: 特定の状態組み合わせを検知し、物語上の特異点（イベント）を発生させる。
- `InteractionStateFormatter`: 数値的な状態を、LLMが理解可能な自然言語の指示や制約に変換する。

### 3.2 統合フロー
`ConnectionPipeline` において、各シーンのフィードバック処理後に以下の順序で実行されます。
1. **状態更新**: `InteractionManager.update_states()` により、現在の状態を行列演算して次状態を算出。
2. **トリガー検知**: `TriggerRegistry` を通じて、状態遷移に伴うドラマチック・トリガー（例：覇権崩壊）がないかチェック。
3. **プロンプト反映**: `InteractionStateFormatter` を使い、算出した状態を次シーンのペルソナ指示や描写制約に注入。

## 4. 運用・調整ガイドライン
### 4.1 係数の調整 (`interaction_matrix.yaml`)
- **正の値 (Promotion)**: 促進。ある状態が高まると、もう一方も引きずられて高まる。
- **負の値 (Inhibition)**: 抑制。ある状態が高まると、もう一方が抑え込まれる。
- **調整のコツ**:
    - 強い対立構造を作りたい場合は、`hegemony` $\leftrightarrow$ `resonance` の間に強い負の係数を設定してください。
    - 安定した関係から緩やかに変化させたい場合は、`decay_rate` を $1.0$ に近づけ、行列係数を小さく（$0.01 \sim 0.1$）設定してください。

### 4.2 新しいカーネルの追加手順
1. `KernelState` モデルに新しい属性を追加。
2. `interaction_matrix.yaml` の行列に新しい行と列を追加し、既存カーネルとの相互作用係数を定義。
3. `InteractionManager` の計算ロジックは動的に行列を処理するため、基本的には変更不要。
4. `InteractionStateFormatter` に新しい状態に対する言語変換ロジックを追加。

## 5. 検証方法
- `tests/state/test_interaction_manager.py`: 行列演算の基本正当性テスト。
- `tests/state/test_interaction_simulation.py`: ドラマチックな状態遷移（アーク）が再現されるかのシミュレーションテスト。
