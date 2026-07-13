# Kernel Interaction Matrix (KIM) 仕様書

## 1. 目的
各カーネル（Resonance, Hegemony, Conflict, Serenity等）の状態を数値化し、それらが互いにどう影響し合うかを定義することで、人間らしい複雑な感情変動とドラマチックな展開を自動生成する。

## 2. 数学的定義
各カーネルの状態をベクトル $\mathbf{S}$ で表す。
$\mathbf{S} = [s_{res}, s_{heg}, s_{con}, s_{ser}]^T$
ここで $s_i \in [0, 100]$ とする。

### 2.1 相互作用更新式
次状態 $\mathbf{S}_{t+1}$ は、現在の状態 $\mathbf{S}_t$ と外部からの刺激 $\mathbf{I}_t$、および相互作用行列 $\mathbf{M}$ によって決定される。

$\mathbf{S}_{t+1} = \text{clamp}(\mathbf{S}_t + \mathbf{M} \mathbf{S}_t + \mathbf{I}_t, 0, 100)$

- $\mathbf{M}$: 相互作用行列（Interaction Matrix）。$M_{ij}$ はカーネル $j$ がカーネル $i$ に与える影響係数。
- $\mathbf{I}_t$: 外部刺激（シーン内での出来事による直接的な変動）。
- $\text{clamp}$: 値を $[0, 100]$ の範囲に制限する。

### 2.2 行列 $\mathbf{M}$ の初期設計案
| 影響元 $\to$ 先 | Resonance | Hegemony | Conflict | Serenity |
| :--- | :---: | :---: | :---: | :---: |
| **Resonance** | 0.05 | -0.1 | -0.1 | 0.1 |
| **Hegemony** | -0.2 | 0.05 | 0.2 | -0.2 |
| **Conflict** | -0.1 | 0.1 | 0.05 | -0.3 |
| **Serenity** | 0.2 | -0.1 | -0.2 | 0.05 |

- **正の値**: 促進（例：Serenity $\to$ Resonance は、静謐な状態が共鳴を深める）
- **負の値**: 抑制（例：Hegemony $\to$ Resonance は、覇権争いが共鳴を阻害する）

## 3. ドラマチック・トリガー (Dynamic Triggers)
特定の条件を満たしたとき、行列演算とは別に「相転移」のような急激な変化を発生させる。

- **例：覇権崩壊による共鳴爆発 (Hegemony Collapse $\to$ Resonance Burst)**
  - 条件: $s_{heg}$ が急落し、かつ $s_{res}$ が一定以上の閾値にある。
  - 効果: $s_{res}$ を強制的に最大値付近まで跳ね上げ、特殊な共鳴イベントを生成する。

## 4. 実装上の制約
- 計算コストを低く抑えるため、行列演算はシーン終了時または重要なイベント発生時のみ実行する。
- 設定ファイル (`interaction_matrix.yaml`) により、係数を動的に変更可能とする。
