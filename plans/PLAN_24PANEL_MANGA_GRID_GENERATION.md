# 24コマ漫画グリッド生成 実装計画書

## 概要
1枚の画像で24コマ（4列×6行）の漫画を生成し、エピソード単体の流れが一目で分かるようにする。

## 目標
- 安定したグリッド構造での生成成功率 90%以上
- キャラクター一貫性維持
- 読み順（右上→左下Z字）が自明
- SNS投稿・印刷同人誌両対応

---

## フェーズ1: 基盤プロンプト設計（Day 1-2）

### 1.1 マスタープロンプトテンプレート確立
```yaml
base_prompt: |
  manga page, 24 panels in 4x6 grid, white gutters 4px, right-to-left reading order,
  panel numbers top-right small, Japanese shonen manga style, screentone shading,
  high contrast lineart, each panel distinct scene chronological story flow,
  masterpiece, best quality

negative_prompt: |
  broken grid, uneven panels, missing gutters, blurry, low quality, watermark,
  text overlay, speech bubbles overlapping panels, inconsistent character design,
  western comic style, 3d render, photograph
```

### 1.2 パラメータ固定値
| パラメータ | 値 | 理由 |
|------------|-----|------|
| `--ar` | `2:3` | 縦長=A5/B5見開き互換、スマホ縦画面最適 |
| `--niji` | `6` | アニメ/マンガ特化 |
| `--style` | `expressive` | 線画強調・スクリーントーン再現性高 |
| `--stylize` | `250-400` | 構成優先（低め）〜画質優先（高め）で調整 |
| `--chaos` | `0-10` | グリッド崩れ防止で極小 |

### 1.3 シード管理戦略
- **キャラ固定用**: 同一シードでキャラシート生成 → 参照画像として `--cref` 使用
- **構図固定用**: グリッド構造のみのラフ生成 → `--cref` + `--cw 100` で構図固定
- **バリエーション用**: ストーリーボード段階で複数シード試行、ベスト採用

---

## フェーズ2: ストーリーボード→プロンプト分解（Day 2-3）

### 2.1 24ビート構成テンプレート
```
Beat  1-3  : 導入（日常/フック）          - 引き〜中景中心
Beat  4-6  : 事件発生/きっかけ            - 寄り増やす
Beat  7-9  : 混乱/試行錯誤                - アクション・表情寄り
Beat 10-12 : 転機/気づき（中盤クライマックス） - 大コマ級の寄り
Beat 13-15 : 対決/核心（山場）            - 最寄り・インパクト構図
Beat 16-18 : 決着/クライマックス           - 全身/エフェクト大
Beat 19-21 : 余韻/変化                    - 引き戻し・環境描写
Beat 22-24 : 結末/次回への伏線             - 引き・記号的締め
```

### 2.2 パネル別プロンプト構造
```json
{
  "panel": 1,
  "beat": "導入",
  "shot": "wide",
  "camera": "establishing shot, classroom morning",
  "characters": ["protagonist:sit:desk", "friend:stand:beside"],
  "expression": "protagonist:neutral, friend:cheerful",
  "key_items": ["schoolbag", "window_light"],
  "mood": "peaceful",
  "panel_prompt": "panel 1, wide shot, classroom morning light, protagonist sitting at desk neutral expression, friend standing beside cheerful, schoolbag on desk, window light rays, peaceful atmosphere"
}
```

### 2.3 自動生成スクリプト仕様（Python）
```python
# generate_panel_prompts.py
- 入力: あらすじJSON / テキスト
- 処理: LLMで24ビート分解 → パネル別プロンプト生成
- 出力: panels_prompts.json (24件)
- 機能: キャラ名/外見辞書参照、ショット種別自動割当
```

---

## フェーズ3: 生成パイプライン構築（Day 3-5）

### 3.1 アーキテクチャ
```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Story JSON │ ──▶ │ Prompt Builder│ ──▶ │ 24 Panel Prompts│
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                    ┌──────────────┐               │
                    │  Grid Composer│ ◀────────────┘
                    │  (ImageMagick/│
                    │   PIL合成)    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Final 24panel│
                    │   Image      │
                    └──────────────┘
```

### 3.2 生成戦略：2段階方式（推奨）
**Stage A: 個別コマ生成（24回API呼び出し）**
- 各コマ最適プロンプトで生成
- 失敗時リトライ容易
- キャラ一貫性: `--cref` キャラ参照画像統一

**Stage B: グリッド合成（ローカル処理）**
- ImageMagick / PIL で 4×6 グリッド合成
- ガター幅・番号・矢印オーバーレイ完全制御
- 解像度: 2048×3072px (4×512, 6×512) 以上推奨

> **代替: 単発生成**  
> `--ar 2:3` で24コマ一発生成も可能だが、コマ割り崩れ・キャラ崩壊リスク高。検証用に併用。

### 3.3 品質ゲート（自動判定）
```python
def quality_check(panel_img, panel_idx):
    checks = {
        "grid_alignment": detect_grid_lines(panel_img),  # エッジ検出でグリッド確認
        "character_consistency": clip_similarity(panel_img, char_reference),  # CLIPスコア
        "readability": ocr_panel_number(panel_img) == panel_idx,  # 番号認識
        "no_artifact": blur_detection(panel_img) < threshold
    }
    return all(checks.values())
```

---

## フェーズ4: キャラクター一貫性システム（Day 4-6）

### 4.1 キャラリファレンスシート生成
```bash
# 1回だけ実行、以降全エピソード共用
midjourney /imagine "character sheet, protagonist, multiple angles, expressions, 
  full body, front side back, close up face, manga style, white background, 
  model sheet --ar 1:1 --niji 6 --style expressive"
```
→ 生成されたベスト1枚を `char_ref/protagonist.png` として保存

### 4.2 参照画像活用パターン
| 用途 | パラメータ | 効果 |
|------|------------|------|
| キャラ顔固定 | `--cref char_ref/protagonist.png --cw 100` | 顔・髪・服装の一貫性最大 |
| 構図固定 | `--cref grid_template.png --cw 50` | グリッド枠・ガター位置固定 |
| スタイル固定 | `--sref style_ref.png --sw 50` | スクリーントーン・線画タッチ統一 |

### 4.3 複数キャラ対応
- メインキャラ2-3人まで: 個別リファレンス画像作成、プロンプトで `character:ref_name` 指定
- モブ/背景キャラ: プロンプトのみで指定、参照画像なし

---

## フェーズ5: 実装タスク分解

| ID | タスク | 担当 | 期間 | 成果物 |
|----|--------|------|------|--------|
| T1 | マスタープロンプト・ネガティブ確定 | - | Day 1 | `prompts/base.yaml` |
| T2 | 24ビート→パネルプロンプト自動生成スクリプト | - | Day 2-3 | `scripts/gen_panel_prompts.py` |
| T3 | キャラリファレンスシート生成・検証 | - | Day 3 | `char_ref/*.png` |
| T4 | 単発生成テスト（5-10枚） | - | Day 3-4 | 生成画像・品質ログ |
| T5 | 2段階パイプライン実装（個別→合成） | - | Day 4-5 | `scripts/pipeline.py` |
| T6 | 品質ゲート自動化 | - | Day 5 | `scripts/quality_gate.py` |
| T7 | エンドツーエンドテスト（3エピソード） | - | Day 6 | 完成画像3枚・評価レポート |
| T8 | ドキュメント・運用ガイド整備 | - | Day 6 | `docs/manga24_guide.md` |

---

## フェーズ6: 検証・評価指標

### 6.1 定量指標
| 指標 | 目標 | 測定方法 |
|------|------|----------|
| グリッド崩れ率 | < 10% | エッジ検出+グリッド線検出 |
| キャラ一貫性 (CLIP) | > 0.85 | 参照画像との類似度 |
| パネル番号認識率 | 100% | OCR (Tesseract) |
| 生成時間/エピソード | < 10分 | パイプライン実行時間 |

### 6.2 定性チェックリスト
- [ ] 右上→左下Z字でストーリーが自然に追える
- [ ] 主人公の顔・服装が全コマでブレない
- [ ] 重要ビート（12, 15, 18, 24コマ目）が視覚的に強調されている
- [ ] 吹き出し・効果音スペースが確保されている（後からテキスト追加可能）
- [ ] サムネイル(320px幅)でもコマ割り判読可能

---

## リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| Midjourney API制限/コスト | 高 | ローカル合成方式でAPI呼び出し最小化、バッチ実行 |
| キャラ崩壊（特に横顔・後ろ姿） | 高 | リファレンスに多角度含める、失敗コマのみリロール |
| グリッド線ズレ・ガター不均一 | 中 | Stage Bローカル合成で物理的に矯正 |
| 24コマプロンプト作成工数 | 中 | LLM自動生成スクリプトで半自動化 |
| 解像度不足（印刷用） | 低 | アップスケーラー (Real-ESRGAN等) 後処理で対応 |

---

## 今後の拡張（Phase 2+）

1. **台詞自動配置**: 生成後に吹き出し+テキスト自動合成
2. **動画化**: 24コマをパラパラアニメ/GIF/MP4出力
3. **多言語対応**: 台詞レイヤー分離で翻訳差し替え容易化
4. **インタラクティブWebビューア**: コマクリックで拡大・台詞表示

---

## 即時アクション（今日やること）

1. [ ] `prompts/base.yaml` 作成（マスタープロンプト確定）
2. [ ] 主人公キャラリファレンスシート生成（Midjourney/WebUIで5-10枚試行→ベスト1枚選定）
3. [ ] テスト用ショートストーリー（24ビート）1本用意
4. [ ] 単発生成で3-5枚テスト → 品質確認

---

## ファイル構成（リポジトリ）
```
project/
├── prompts/
│   ├── base.yaml           # マスタープロンプト
│   └── panel_templates/    # ビート別プロンプトテンプレ
├── char_ref/
│   ├── protagonist.png
│   ├── friend.png
│   └── rival.png
├── scripts/
│   ├── gen_panel_prompts.py
│   ├── pipeline.py
│   └── quality_gate.py
├── style_ref/
│   └── manga_style.png
├── output/
│   ├── panels/             # 個別コマ (生成直後)
│   └── final/              # 合成済み24コマ画像
├── docs/
│   └── manga24_guide.md
└── stories/
    └── episode_001.json    # あらすじ・24ビート定義
```

---

**承認待ち**: この計画で実装を開始してよいか？ 修正点があれば指示を。