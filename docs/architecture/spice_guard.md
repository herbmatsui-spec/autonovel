# SpiceGuard (尖り保護システム) アーキテクチャ

## 概要

SpiceGuard は、自動リライト時に「この話の命」となる尖り要素（独自比喩・キャラ声・伏線・生々しい感情・ジャンル専用語彙）を検出・保護・復元するシステムです。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                     EpisodeRewriter                          │
├─────────────────────────────────────────────────────────────┤
│  1. extract_spice(text) → List[SpiceElement]                │
│  2. inject_markers(text, spices) → marked_text              │
│  3. LLM リライト (マーカー変更禁止指示付き)                   │
│  4. remove_markers(rewritten) → clean_text                  │
└─────────────────────────────────────────────────────────────┘
```

## データ構造

```python
@dataclass
class SpiceElement:
    type: str           # "metaphor" | "catchphrase" | "foreshadowing" | "emotion" | "genre_vocab"
    text: str           # 元のテキスト
    position: int       # 文字位置
    confidence: float   # 0.0-1.0
```

## 検出ロジック (抽出フェーズ)

### 1. 独自比喩 (Metaphor)
- パターン: `まるで.*のよう`, `.*かのように`, `まるで.*だ`
- キーワードベース + 形態素解析で比喩構造を検出

### 2. キャラ声・キャッチフレーズ (Catchphrase)
- プリセット定義 `characters/char_archetypes_{genre}.json` からキャラごとの禁句・口癖を読み込み
- 完全一致・部分一致で検出

### 3. 伏線・回収 (Foreshadowing)
- キーワード: `実は`, `真真`, `正体`, `覚醒`, `伏線`, `回収`, `種明かし`
- 前後文脈で「伏線張り」vs「伏線回収」を区別

### 4. 生々しい感情 (Emotion)
- 身体感覚語: `胸が締め付け`, `背筋が凍る`, `鳥肌`, `息が詰まる`, `震える`
- 感情強度スコアリング (0-100) で閾値以上を抽出

### 5. ジャンル専用語彙 (Genre Vocabulary)
- 各ジャンルの `episode_structure/episode_structure_{genre}.yaml` に定義
- キーワード例:
  - ざまぁ: `ざまぁ`, `無双`, `圧倒的`, `顔面蒼白`, `カタルシス`
  - 悪役令嬢: `フラグ`, `隠しルート`, `百合`, `尊い`, `契約`
  - チート転生: `スキル`, `秒殺`, `最適解`, `デバッグ`, `システム`

## マーカー形式

```
<<<SPICE:{type}_{index}>>>元のテキスト<<</SPICE>>>
```

例:
```
<<<SPICE:metaphor_0>>>まるで絶望の底から這い上がったかのように<<</SPICE>>>
```

## 類似度判定 (SemanticEdgePreserver)

SpiceGuard と連携し、リライト後のテキストでマーカー内容が意味的に保持されているか判定:

- 埋め込みベクトル (text-embedding-004) で元テキストとリライト後テキストのコサイン類似度計算
- 閾値: **0.75** (Settings.similarity_threshold)
- 0.75 未満の場合は「尖りが失われた」と判定し、再リライトまたは人間レビューフラグ

### 閾値 0.75 の根拠

| 類似度 | 判定 | 根拠 |
|--------|------|------|
| ≥ 0.85 | 完全保持 | 言い換えレベル |
| 0.75-0.84 | 十分保持 | ニュアンス維持 |
| 0.60-0.74 | 要注意 | 核心は残るが表現変化大 |
| < 0.60 | 失われた | 意味が大きく変質 |

実験的に 0.75 が「自動リライトで許容できる最小限の保持ライン」かつ「誤検知が少ない」バランスポイント。

## リライトプロンプト指示

```
以下のマーカーで囲まれた部分は「この話の命」です。
絶対に変更・削除・言い換えしないでください。

<<<SPICE:metaphor_0>>>まるで絶望の底から這い上がったかのように<<</SPICE>>>
```

## フロー図

```
原文
  │
  ▼
[extract_spice] ──→ SpiceElement[]
  │
  ▼
[inject_markers] ──→ マーカー付きテキスト
  │
  ▼
[LLMリライト] (マーカー保護指示付き)
  │
  ▼
[remove_markers] ──→ クリーンなリライト済みテキスト
  │
  ▼
[SemanticEdgePreserver.verify] ──→ 類似度 ≥ 0.75 ?
  │                    ├─ Yes → 完了
  │                    └─ No  → 再リライト / 人間レビューフラグ
```

## 設定パラメータ (Settings)

| パラメータ | デフォルト | 説明 |
|------------|------------|------|
| `similarity_threshold` | 0.75 | 意味的保持判定閾値 |
| `enable_semantic_edge_preservation` | true | SemanticEdgePreserver 有効化 |
| `enable_spice_guard` | true | SpiceGuard 全体有効化 (PipelineConfig) |
| `max_rewrite_iterations` | 3 | 最大リライト回数 |

## パフォーマンス最適化

- **逆インデックス**: 語彙 → 登場位置 のマッピングで O(n) 検索を O(1) に高速化
- **キャッシュ**: 同一テキストの抽出結果を意味的キャッシュ (ChromaDB) に保存
- **並列処理**: 話数ごとに独立して抽出・リライト実行可能

## テスト

- `tests/unit/test_sharp_edge_preserver.py`: 類似度判定ロジック
- `tests/phase2/test_phase2_pipeline_integration.py`: 統合テスト (尖り保護含む E2E)