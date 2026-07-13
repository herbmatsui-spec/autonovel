# erotic_vocabulary intense tier 拡張 実装計画

## 前提条件・現在の状態

### 既存ファイルの把握

| ファイル | 状態 | 役割 |
|---|---|---|
| `config/erotic_vocabulary.py` | 存在済 | `mild`/`moderate`/`full` の3ティアを管理。`get_vocabulary_for_tier(tier)` を提供 |
| `config/erotic_vocabulary_ext.py` | 骨子のみ存在 | `intense` ティアの下書き（`INTENSE_METAPHORS`=10、`INTENSE_ONOMATOPOEIA`=5、`INTENSE_PSYCHOLOGY`=5）が定義済み |
| `config/erotic_platform_presets.py` | 存在済 | `adult_selfhost` プリセットが `allowed_vocabulary_tier: "intense"` を指す |
| `config/__init__.py` | 存在済 | `erotic_vocabulary` のみエクスポート。`erotic_vocabulary_ext` は未エクスポート |
| `src/engine/prompts/erotic_specialist.py:33` | 問題箇所 | `get_vocabulary_for_tier(preset.get("allowed_vocabulary_tier"))` に `"intense"` が渡されるが、元の関数は `intense` に対応していない |

### 強度5 (過激) とティアの対応

```
intensity 5 (過激)  →  vocabulary tier "intense"  →  adult_selfhost プリセット
```

---

## 問題分析

1. **`get_vocabulary_for_tier("intense")` の呼び出しが失敗する**  
   - `erotic_vocabulary.py` の `VOCABULARY_TIERS` に `"intense"` キーが存在しない  
   - `get_vocabulary_for_tier` は未対応ティアを `mild` にフォールバックするため、`intense` 指定が無視される

2. **`erotic_vocabulary_ext.py` の `get_vocabulary_for_tier_ext` が使われていない**  
   - `erotic_specialist.py` が元の `get_vocabulary_for_tier` を直接呼んでいる

3. **`intense` ティアのボキャブラリが量が不十分**  
   - 現在 `INTENSE_METAPHORS`=10、`INTENSE_ONOMATOPOEIA`=5、`INTENSE_PSYCHOLOGY`=5 しかない  
   - tier 間の量的バランス来看、`mild`=30、`moderate`=96、`full`=141 に対し `intense`=121 は明らかに少ない

4. **`adult_selfhost` プリセット使用時に `intense` ティアが有効にならない**

---

## 48ステップ実装計画

### Phase A: 分析・調査 (Steps 1-6)

- **Step 1**: `erotic_specialist.py` の `get_vocabulary_for_tier` 呼び出し箇所を完全調査し、呼び出しチェーンを追跡
- **Step 2**: テスト suite (`tests/test_erotic*.py`) で `intense` / `erotic_vocabulary_ext` に関連するテストをリストア
- **Step 3**: `VOCABULARY_TIERS` 各ティアのサイズ（metaphors/onomatopoeia/psychology の各リスト長）を記録し、要件との差距を算出
- **Step 4**: `config/erotic_pacing.py` の `EroticCurve` における `target_intensity` と vocabulary tier の紐付けロジック是否存在を確認
- **Step 5**: `adult_selfhost` プリセット使用时の vocabulary tier 解決路径（プロンプト生成 → formatter → censor）を追踪
- **Step 6**: 既存の `intense` ボキャブラリ重複を確認し、base の `full` tier と重複しているアイテムを特定

### Phase B: アダプター統合 (Steps 7-15)

- **Step 7**: `config/erotic_vocabulary.py` に `get_vocabulary_for_tier` の内部で `erotic_vocabulary_ext` をインポートするフォールバックロジック追加（循環参照にならないよう遅延インポート）
- **Step 8**: `config/__init__.py` に `erotic_vocabulary_ext` からのエクスポートを追加（`get_vocabulary_for_tier_ext`、`VOCABULARY_TIERS_EXT`、`INTENSE_*` 定数）
- **Step 9**: `src/engine/prompts/erotic_specialist.py` を修正し、`get_vocabulary_for_tier` の呼び出しを `get_vocabulary_for_tier_ext` に切り替え
- **Step 10**: 切り替えに伴い `erotic_specialist.py` のインポート文を更新
- **Step 11**: `erotic_specialist.py` 以外の箇所で `get_vocabulary_for_tier` を呼んでいるファイルをすべてリストアップ
- **Step 12**: 追加の呼び出し箇所すべてのインポートと呼び出しを `get_vocabulary_for_tier_ext` に统一修正
- **Step 13**: 循環参照が発生しないことを `python -c "from config import get_vocabulary_for_tier_ext; print('ok')"` で検証
- **Step 14**: `config/__init__.py` 再インポート確認 `python -c "from config import get_vocabulary_for_tier"` が引き続き動作することを確認
- **Step 15**: 修正后的 backward compatibility 確認：既存の `get_vocabulary_for_tier("mild")` 等が引き続き動作すること

### Phase C: intense ボキャブラリ拡張 (Steps 16-30)

#### Step 16-18: 量的ギャップ分析と目標値設定
- **Step 16**: `full` tier の総語彙数（141アイテム）を基准に `intense` tier の目标総数を决定（少なくとも `full` + 50 = 191以上を目標）
- **Step 17**: 各カテゴリ（metaphors/onomatopoeia/psychology）每の目标数を算出
- **Step 18**: 現在の不足数（metaphors 目標-現在=?, onomatopoeia 目標-現在=?, psychology 目標-現在=?）を算出

#### Step 19-23: `INTENSE_METAPHORS` 拡張（+25 アイテム追加）
- **Step 19**: 既存 `INTENSE_METAPHORS` と `METAPHOR_BANK` の重複チェック・除外リスト作成
- **Step 20**: 強度5向けの身体感覚の比喩（体温の溶解感、重力の消失、境界の崩壊）25アイテムを新規作成
- **Step 21**: 各アイテムを「官能過激度」が高い順に並べ替え
- **Step 22**: `erotic_vocabulary_ext.py` の `INTENSE_METAPHORS` を拡張版で置換
- **Step 23**: 拡張後の `intense["metaphors"]`総数が目標値を超えたことを手計算で確認

#### Step 24-27: `INTENSE_ONOMATOPOEIA` 拡張（+15 アイテム追加）
- **Step 24**: 呼吸・脈拍・体液の音・触感плагиат防止のための独自性チェック
- **Step 25**: 五感（視覚・聴覚・触覚・嗅覚・味覚）別の強度5向け擬音語・擬態語15アイテムを新規作成
- **Step 26**: `INTENSE_ONOMATOPOEIA` を拡張版で置換
- **Step 27**: 拡張後の `intense["onomatopoeia"]` 合計を確認

#### Step 28-30: `INTENSE_PSYCHOLOGY` 拡張（+15 アイテム追加）
- **Step 28**: 精神崩壊・快感の洪水・自我の消失・衝動の制御不能などの心理テンプレート15アイテムを新規作成
- **Step 29**: `INTENSE_PSYCHOLOGY` を拡張版で置換
- **Step 30**: 全カテゴリ合計語彙数が目標（191+以上）を達成したことを確認

### Phase D: 統合・テスト (Steps 31-42)

- **Step 31**: `tests/test_erotic_workflow.py::test_intense_tier_accessible` を実行し、`intense["metaphors"] >= full["metaphors"]` が PASS することを確認
- **Step 32**: `tests/test_erotic_workflow.py::test_full_tier_minimum_vocabulary` が引き続き PASS することを確認
- **Step 33**: 新しいボキャブラリアイテムに対して重複チェック（集合に変換して長さ比較）
- **Step 34**: `adult_selfhost` プリセット使用時に强度5で生成されるプロンプトに変数が正しく挿入されるか `python -c` で简易テスト
- **Step 35**: 循環参照テスト：`from config.erotic_vocabulary_ext import get_vocabulary_for_tier_ext; from config.erotic_vocabulary import get_vocabulary_for_tier; print(get_vocabulary_for_tier_ext("intense")["metaphors"][:3])`
- **Step 36**: `mild`/`moderate`/`full` が `get_vocabulary_for_tier_ext` でも使用可能か確認（委譲テスト）
- **Step 37**: integration test (`tests/integration/test_erotic_full_pipeline.py::test_vocabulary_tier_intensity_mapping`) を実行
- **Step 38**: `_test_erotic.py` を実行して全チェックをPASSさせる
- **Step 39**: `_compile_check.py` を実行して import error がないことを確認
- **Step 40**: `pytest tests/test_erotic*.py -v` で関連テストを一括実行
- **Step 41**: `mypy config/erotic_vocabulary_ext.py --ignore-missing-imports` で型ヒント検証
- **Step 42**: `ruff check config/erotic_vocabulary_ext.py` でリントチェック

### Phase E: ドキュメンテーション・完了 (Steps 43-48)

- **Step 43**: `config/erotic_vocabulary_ext.py` の docstring を完成させ、各定数の説明を記載
- **Step 44**: `INTENSE_METAPHORS`/`INTENSE_ONOMATOPOEIA`/`INTENSE_PSYCHOLOGY` の先頭にコメントで各カテゴリの特徴を記載
- **Step 45**: `erotic_intensity_standards.md` 或者其他ドキュメントに `intense` tier の説明を追加
- **Step 46**: この実装計画ファイル（`plans/erotic_intense_implementation.md`）を更新し、各ステップの実施可否を記入
- **Step 47**: `IMPLEMENTATION_PLAN_V4.md` または `WORK_PRODUCTION_REPORT.md` に本改善的实施状況を記録
- **Step 48**: 全テスト PASS を確認し、最終的なボキャブラリサイズを表にまとめる

---

##  erwartete 成果物

### ファイル変更

| ファイル | 変更内容 |
|---|---|
| `config/erotic_vocabulary.py` | `get_vocabulary_for_tier` 内に遅延インポートで `intense` をハンドリング |
| `config/erotic_vocabulary_ext.py` | 3カテゴリすべてを大幅拡張（目標: 合計191+アイテム） |
| `config/__init__.py` | `erotic_vocabulary_ext` のエクスポートを追加 |
| `src/engine/prompts/erotic_specialist.py` | `get_vocabulary_for_tier_ext` への切り替え |
| `plans/erotic_intense_implementation.md` | 本計画書（新規） |

### intensive tier 目標サイズ

```
mild     :  30 アイテム (metaphors=10, onomatopoeia=10, psychology=10)
moderate :  96 アイテム (metaphors=40, onomatopoeia=28, psychology=25+3)
full     : 141 アイテム (metaphors=48, onomatopoeia=33, psychology=35+5+20)
intense  : 191+ アイテム (full + intense拡張: metaphors=73, onomatopoeia=53, psychology=50+15)
```

### adult_selfhost プリセットでの强度5利用時フロー

```
user: intensity=5, platform=adult_selfhost
  → get_preset("adult_selfhost")["allowed_vocabulary_tier"] = "intense"
  → get_vocabulary_for_tier_ext("intense")  # 拡張ティア対応版
  → VOCABULARY_TIERS_EXT["intense"] を返す
  → intense tier の全ボキャブラリをプロンプトに挿入
```

---

## リスクと対策

| リスク | 対策 |
|---|---|
| 循環参照 (`erotic_vocabulary.py` → `erotic_vocabulary_ext.py` → `erotic_vocabulary.py`) | 遅延インポート（関数内で import）方式进行 |
| `get_vocabulary_for_tier` の呼び出し元が多い | まず `erotic_specialist.py` を修正し、他の箇所は Step 11-12 で一并対応 |
| 既存の integration test が失敗する | Step 37-38 で必ず全テストを実行して確認 |