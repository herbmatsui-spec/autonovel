# P9: 4層圧縮高度化（Layer 3可逆性・シーン文脈認識・定量的情報保持率）実装計画書（全18ステップ）

**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**目的**:
1. **Layer 3 概念抽象化の可逆性・情報密度向上**: 固有名詞の完全捨象を廃止し、「固有名称＋カテゴリ（例：抜刀・迅雷 [雷撃系近接スキル]）」のデュアル表記で作家性・ディテール再現性を担保。
2. **シーン判定のコンテキスト認識向上**: 単純キーワードSoftmaxから、直前シーンフロー（履歴推移）やエピソード主目的（プロットビート）を加味したコンテキスト考慮型シーン分類器へ強化。
3. **定量的評価指標の導入**: トークン削減率だけでなく、「次エピソード生成時のキャラクター・伏線整合性スコア（情報保持率・整合性メトリクス）」を自動計測し、テストスイートに組み込む。

**低性能LLM向け設計方針**:
- **全18ステップの極小分割**: 1ステップにつき1〜2ファイルのみの変更。
- **完全自己完結コード**: コピペで動作する完全なコード、インポート文、テストケースを記載。
- **検証コマンドと合否基準**: ステップごとにワンライナー検証コマンドとPass条件を明記。

---

## 📋 全18ステップ 実装マトリクス

| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **Step 1** | 型定義 | [`src/services/compression/models.py`](file:///e:/hhh/src/services/compression/models.py) | 可逆的エンティティ表現型 `ReversibleEntityFact` 及び評価指標モデル `CompressionQualityMetrics` の追加 | `python -c "from src.services.compression.models import ReversibleEntityFact, CompressionQualityMetrics; print('OK')"` |
| **Step 2** | Layer 3 | [`src/services/compression/layer3_taxonomy.py`](file:///e:/hhh/src/services/compression/layer3_taxonomy.py) | 概念一般化エンジンのデュアル表現メソッド（`format_dual_concept`）追加 | `pytest tests/unit/test_dynamic_taxonomy.py -o addopts="" --no-cov` |
| **Step 3** | Layer 3 | [`src/services/compression/layer3_abstraction.py`](file:///e:/hhh/src/services/compression/layer3_abstraction.py) | ノード事実のデュアルフォーマット化（`固有名称 [概念カテゴリ]`）実装 | `pytest tests/unit/test_layer3_dynamic_abstraction.py -o addopts="" --no-cov` |
| **Step 4** | Layer 3 | [`src/services/compression/layer3_abstraction.py`](file:///e:/hhh/src/services/compression/layer3_abstraction.py) | エッジ関係性のデュアルフォーマット化（`A と B は 関係名 [一般関係]`）実装 | `pytest tests/unit/test_layer3_dynamic_abstraction.py -o addopts="" --no-cov` |
| **Step 5** | Layer 3テスト | `tests/unit/test_layer3_reversible_abstraction.py` | 可逆性・情報密度向上の単体テスト新規作成と検証 | `pytest tests/unit/test_layer3_reversible_abstraction.py -o addopts="" --no-cov` |
| **Step 6** | シーン型定義 | [`src/services/compression/models.py`](file:///e:/hhh/src/services/compression/models.py) | 直前シーン履歴（`SceneFlowHistory`）及びエピソード主目的パラメータの定義 | `python -c "from src.services.compression.models import SceneFlowHistory; print('OK')"` |
| **Step 7** | シーン遷移 | [`src/services/compression/layer4_trimming.py`](file:///e:/hhh/src/services/compression/layer4_trimming.py) | シーン遷移確率マトリクス（マルコフ遷移重み）の定義 | `python -c "from src.services.compression.layer4_trimming import SCENE_TRANSITION_MATRIX; print(len(SCENE_TRANSITION_MATRIX))"` |
| **Step 8** | シーン分類器 | [`src/services/compression/layer4_trimming.py`](file:///e:/hhh/src/services/compression/layer4_trimming.py) | 文脈履歴・プロットビートを考慮した `detect_scene_context_aware` メソッド実装 | `pytest tests/unit/test_layer4_multiscene.py -o addopts="" --no-cov` |
| **Step 9** | Layer 4反映 | [`src/services/compression/layer4_trimming.py`](file:///e:/hhh/src/services/compression/layer4_trimming.py) | `trim` メソッドでのデュアル表記パースとカテゴリ重み付けの連動 | `pytest tests/unit/test_layer4_multiscene.py -o addopts="" --no-cov` |
| **Step 10** | シーンテスト | `tests/unit/test_context_aware_scene_detection.py` | 直前シーン履歴・作戦会議などの文脈反転を判定する単体テスト新規作成 | `pytest tests/unit/test_context_aware_scene_detection.py -o addopts="" --no-cov` |
| **Step 11** | 評価指標関数 | `src/services/compression/metrics.py` | キャラクター・伏線・固有名詞の整合性スコア算出関数（`calculate_consistency_metrics`）新規作成 | `python -c "from src.services.compression.metrics import calculate_consistency_metrics; print('OK')"` |
| **Step 12** | 統合クラス更新 | [`src/services/compression/compressor.py`](file:///e:/hhh/src/services/compression/compressor.py) | `FourLayerCompressor.compress` へのシーン文脈伝搬と品質メトリクス計測組み込み | `pytest tests/unit/test_compression_pipeline.py -o addopts="" --no-cov` |
| **Step 13** | パッケージ公開 | [`src/services/compression/__init__.py`](file:///e:/hhh/src/services/compression/__init__.py) | 新設したメトリクス・シーン履歴・デュアルモデルのエクスポート | `python -c "from src.services.compression import calculate_consistency_metrics, SceneFlowHistory; print('OK')"` |
| **Step 14** | Agent連携 | [`src/agents/context_builder_agent.py`](file:///e:/hhh/src/agents/context_builder_agent.py) | 直前エピソードのシーン履歴とプロット主目的をコンプレッサーに渡す改修 | `python -c "import src.agents.context_builder_agent; print('Agent load OK')"` |
| **Step 15** | 定量評価テスト | `tests/unit/test_compression_consistency_metrics.py` | 圧縮前後のキャラクター保持率・伏線保持率・整合性スコアの単体テスト | `pytest tests/unit/test_compression_consistency_metrics.py -o addopts="" --no-cov` |
| **Step 16** | ベンチマーク | `tests/benchmarks/benchmark_consistency_and_reduction.py` | トークン削減率 vs キャラ・伏線保持率のトレードオフベンチマークスクリプト作成 | `python tests/benchmarks/benchmark_consistency_and_reduction.py` |
| **Step 17** | 総合回帰検証 | 全ユニットテスト | 圧縮パイプライン関連の全テストスイート一括実行 | `pytest tests/unit/test_*compression*.py tests/unit/test_layer*.py -o addopts="" --no-cov` |
| **Step 18** | ドキュメント更新 | `docs/architecture/COMPRESSION_REVERSIBLE_PIPELINE.md` | デュアル抽象化仕様、文脈シーン遷移、品質メトリクスの設計仕様書を整備 | `python -c "import os; assert os.path.exists('docs/architecture/COMPRESSION_REVERSIBLE_PIPELINE.md')"` |

---

## 🛠 各ステップ詳細仕様

### Step 1: モデル定義拡張 (`ReversibleEntityFact`, `CompressionQualityMetrics`)
- **目的**: 固有名詞と概念のデュアル保持用モデルおよび定量評価指標モデルを定義する。
- **対象ファイル**: [`src/services/compression/models.py`](file:///e:/hhh/src/services/compression/models.py)
- **編集内容**:
  以下のクラス定義を `models.py` に追加し、`__all__` に含める。
```python
# src/services/compression/models.py に追加
class ReversibleEntityFact(BaseModel):
    """固有名詞と抽象概念を併保持するデュアル表現 (Layer 3)"""
    entity: str = Field(description="元の固有名詞（例：抜刀・迅雷）")
    concept: str = Field(description="一般化された抽象概念（例：雷撃系近接スキル）")
    category: str = Field(description="所属カテゴリ（例：武術・スキル）")
    raw_fact: str = Field(description="抽出元の元テキストまたは属性")
    
    @property
    def display_text(self) -> str:
        """執筆プロンプト用のデュアル表現形式"""
        if self.concept and self.concept != self.entity:
            return f"{self.entity} [{self.concept}]"
        return self.entity


class CompressionQualityMetrics(BaseModel):
    """圧縮品質・情報保持率の定量的評価指標"""
    character_retention_score: float = Field(default=1.0, description="登場人物の保持率 (0.0 - 1.0)")
    foreshadowing_retention_score: float = Field(default=1.0, description="未回収伏線の保持率 (0.0 - 1.0)")
    proper_noun_retention_score: float = Field(default=1.0, description="主要固有名詞の残存率 (0.0 - 1.0)")
    semantic_density_score: float = Field(default=1.0, description="トークンあたりの情報密度スコア")
    overall_consistency_score: float = Field(default=1.0, description="総合整合性スコア (加重平均)")
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.models import ReversibleEntityFact, CompressionQualityMetrics; f = ReversibleEntityFact(entity='抜刀・迅雷', concept='雷撃系近接スキル', category='武術・スキル', raw_fact=''); assert f.display_text == '抜刀・迅雷 [雷撃系近接スキル]'; print('Step 1 OK')"
  ```
- **合否基準**: `Step 1 OK` と出力されること。

---

### Step 2: `DynamicTaxonomyEngine` へのデュアル表現整形メソッド追加
- **目的**: 固有名詞と一般化概念を組み合わせたデュアル表記を統一生成する。
- **対象ファイル**: [`src/services/compression/layer3_taxonomy.py`](file:///e:/hhh/src/services/compression/layer3_taxonomy.py)
- **編集内容**:
  `DynamicTaxonomyEngine` クラスに `format_dual_concept` メソッドを追加。
```python
    def format_dual_concept(self, entity_name: str, context: str = "") -> str:
        """固有名詞と一般化概念を '名称 [概念]' のデュアル形式で生成"""
        concept = self.generalize(entity_name, context)
        if concept and concept != entity_name:
            return f"{entity_name} [{concept}]"
        return entity_name
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.layer3_taxonomy import DynamicTaxonomyEngine; engine = DynamicTaxonomyEngine(); res = engine.format_dual_concept('烈火剣'); assert '[' in res; print('Step 2 OK:', res)"
  ```
- **合否基準**: `Step 2 OK: 烈火剣 [近接・物理攻撃スキル]` 等のデュアル形式が出力されること。

---

### Step 3: Layer 3 ノード事実のデュアルフォーマット化
- **目的**: エンティティ事実を「固有名詞 [概念カテゴリ]」形式で保持し、作家性・ディテールを消失させない。
- **対象ファイル**: [`src/services/compression/layer3_abstraction.py`](file:///e:/hhh/src/services/compression/layer3_abstraction.py)
- **編集内容**:
  `Layer3ConceptAbstractor.abstract` 内のノード事実生成部分を修正。
```python
            # 概念の動的一般化
            generalized = self._generalize_concept(name, context=desc)

            # ラベル/タイプ判定
            target_cat = self._detect_category_for_node(labels, generalized, name)

            if generalized:
                abstract_concepts.append(generalized)
                category_mappings.setdefault(target_cat, []).append(f"{name} -> {generalized}")

            # 固有名詞＋概念のデュアル表記（可逆性保持）
            dual_name = f"{name} [{generalized}]" if (generalized and generalized != name) else name
            fact_text = f"{dual_name}（{desc}）" if desc else dual_name

            categorized_facts[target_cat].append({
                "entity": name,
                "concept": generalized or name,
                "dual_name": dual_name,
                "fact": fact_text,
                "category": target_cat,
            })
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_layer3_dynamic_abstraction.py -o addopts="" --no-cov
  ```
- **合否基準**: 既存の Layer 3 テストがすべて Pass すること。

---

### Step 4: Layer 3 エッジ関係性のデュアルフォーマット化
- **目的**: 関係性事実も「A と B は 関係名 [一般関係]」形式で保持する。
- **対象ファイル**: [`src/services/compression/layer3_abstraction.py`](file:///e:/hhh/src/services/compression/layer3_abstraction.py)
- **編集内容**:
  `Layer3ConceptAbstractor.abstract` 内のエッジ事実生成部分を修正。
```python
            # 階層的関係一般化
            generalized_rel = self._generalize_relation(rel)
            target_cat = "主要キャラ"
            if any(k in generalized_rel for k in ["対立", "因縁", "謀略"]):
                target_cat = "伏線"
            elif any(k in generalized_rel for k in ["統治", "領地", "同盟"]):
                target_cat = "地理・勢力"
            elif any(k in generalized_rel for k in ["装備", "遺物", "使役"]):
                target_cat = "アイテム・装備"

            # デュアル関係性表記
            dual_rel = f"{rel} [{generalized_rel}]" if (generalized_rel and generalized_rel != rel) else rel
            edge_fact = f"{src} と {tgt} は「{dual_rel}」の関係"

            categorized_facts[target_cat].append({
                "entity": f"{src}-{tgt}",
                "concept": generalized_rel,
                "dual_name": dual_rel,
                "fact": edge_fact,
                "category": target_cat,
            })
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_layer3_dynamic_abstraction.py -o addopts="" --no-cov
  ```
- **合否基準**: 既存テストがすべて Pass すること。

---

### Step 5: Layer 3 可逆性・情報密度単体テストの新規作成
- **目的**: 固有名詞が捨てられず「名称 [概念]」で保持されていることを明示的にテストする。
- **作成ファイル**: `tests/unit/test_layer3_reversible_abstraction.py`
- **コード内容**:
```python
import pytest
from src.services.compression.layer3_abstraction import Layer3ConceptAbstractor
from src.services.compression.models import SubgraphLayerOutput

def test_layer3_preserves_proper_nouns_with_dual_format():
    abstractor = Layer3ConceptAbstractor()
    subgraph = SubgraphLayerOutput(
        nodes=[
            {"name": "抜刀・迅雷", "labels": ["Skill"], "properties": {"description": "神速の雷撃斬撃"}},
            {"name": "魔剣バルムンク", "labels": ["Item"], "properties": {"description": "竜殺しの呪われし古剣"}},
        ],
        edges=[
            {"source": "抜刀・迅雷", "target": "魔剣バルムンク", "type": "併用奥義"},
        ]
    )
    res = abstractor.abstract(subgraph)
    
    # 武術・スキルに「抜刀・迅雷」と「雷撃系」が両立していること
    skills = res.categorized_facts.get("武術・スキル", [])
    assert any("抜刀・迅雷" in f["fact"] and "[" in f["fact"] for f in skills)
    
    # アイテム・装備に「魔剣バルムンク」と「伝説級」が両立していること
    items = res.categorized_facts.get("アイテム・装備", [])
    assert any("魔剣バルムンク" in f["fact"] and "[" in f["fact"] for f in items)
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_layer3_reversible_abstraction.py -o addopts="" --no-cov
  ```
- **合否基準**: 1 passed で完了すること。

---

### Step 6: シーン文脈履歴モデル `SceneFlowHistory` の定義
- **目的**: 直前数エピソードのシーン履歴とエピソード主目的（ビート）を保持するデータ構造を定義する。
- **対象ファイル**: [`src/services/compression/models.py`](file:///e:/hhh/src/services/compression/models.py)
- **編集内容**:
```python
# src/services/compression/models.py に追加
class SceneFlowHistory(BaseModel):
    """シーン遷移文脈履歴"""
    recent_scene_types: list[SceneType] = Field(default_factory=list, description="直近3〜5話のシーン遷移履歴")
    episode_goal: str = Field(default="", description="本エピソードの主目的（例: 作戦会議・休息・決戦）")
    pacing_tag: str = Field(default="normal", description="テンポ感: setup / confrontation / resolution")
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.models import SceneFlowHistory; s = SceneFlowHistory(recent_scene_types=['combat', 'combat'], episode_goal='宴会'); assert len(s.recent_scene_types) == 2; print('Step 6 OK')"
  ```
- **合否基準**: `Step 6 OK` と出力されること。

---

### Step 7: シーン遷移確率マトリクス（マルコフ遷移重み）の定義
- **目的**: 直前のシーンから「次に起こりやすいシーン」「反動で休息が入るシーン」等の文脈バイアスを定義。
- **対象ファイル**: [`src/services/compression/layer4_trimming.py`](file:///e:/hhh/src/services/compression/layer4_trimming.py)
- **編集内容**:
  `SCENE_TRANSITION_MATRIX` を定義。
```python
# 直前シーンから次シーンへの自然な遷移重み（マルコフ事前分布）
SCENE_TRANSITION_MATRIX: dict[SceneType, dict[SceneType, float]] = {
    "combat": {"daily": 1.4, "psychological": 1.3, "combat": 0.8, "political": 1.1, "romance": 0.9, "mystery": 1.0, "flashback": 1.2, "survival": 1.0, "general": 1.0},
    "daily": {"combat": 1.3, "political": 1.2, "romance": 1.3, "daily": 1.0, "psychological": 1.0, "mystery": 1.2, "flashback": 0.8, "survival": 1.1, "general": 1.0},
    "political": {"combat": 1.3, "psychological": 1.3, "political": 1.1, "mystery": 1.2, "daily": 0.9, "romance": 0.8, "flashback": 1.1, "survival": 0.9, "general": 1.0},
    "psychological": {"combat": 1.2, "flashback": 1.4, "daily": 1.1, "political": 1.1, "romance": 1.1, "mystery": 1.2, "psychological": 0.9, "survival": 1.0, "general": 1.0},
    "romance": {"daily": 1.3, "psychological": 1.3, "combat": 0.9, "political": 0.9, "romance": 1.0, "mystery": 0.8, "flashback": 1.1, "survival": 0.8, "general": 1.0},
    "mystery": {"combat": 1.2, "political": 1.3, "psychological": 1.2, "mystery": 1.0, "daily": 0.9, "romance": 0.8, "flashback": 1.1, "survival": 1.0, "general": 1.0},
    "flashback": {"psychological": 1.4, "combat": 1.2, "daily": 1.0, "political": 1.1, "flashback": 0.5, "romance": 0.9, "mystery": 1.0, "survival": 1.0, "general": 1.0},
    "survival": {"combat": 1.4, "daily": 1.3, "survival": 1.0, "psychological": 1.2, "political": 0.7, "romance": 0.7, "mystery": 0.9, "flashback": 0.8, "general": 1.0},
    "general": {k: 1.0 for k in ["general", "combat", "daily", "psychological", "political", "romance", "mystery", "flashback", "survival"]},
}
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.layer4_trimming import SCENE_TRANSITION_MATRIX; assert SCENE_TRANSITION_MATRIX['combat']['daily'] == 1.4; print('Step 7 OK')"
  ```
- **合否基準**: `Step 7 OK` と出力されること。

---

### Step 8: 文脈考慮型シーン分類器 `detect_scene_context_aware` の実装
- **目的**: キーワード出現頻度だけでなく、直前シーン履歴とエピソード主目的（ビート）を加味して判定。
- **対象ファイル**: [`src/services/compression/layer4_trimming.py`](file:///e:/hhh/src/services/compression/layer4_trimming.py)
- **編集内容**:
```python
    def detect_scene_context_aware(
        self,
        plot_summary: str,
        scenes: list[str] | None = None,
        scene_flow: SceneFlowHistory | None = None,
    ) -> List[Tuple[SceneType, float]]:
        """直前シーン履歴とエピソード主目的を考慮した文脈認識型シーン判定"""
        # 1. 基本キーワードスコアリング
        raw_probs = dict(self.detect_scene_type_multi(plot_summary, scenes))
        
        # 2. 直前シーン履歴によるバイアス補正
        if scene_flow and scene_flow.recent_scene_types:
            last_scene = scene_flow.recent_scene_types[-1]
            transition_weights = SCENE_TRANSITION_MATRIX.get(last_scene, {})
            for s_type in raw_probs:
                bias = transition_weights.get(s_type, 1.0)
                raw_probs[s_type] *= bias
                
        # 3. エピソード主目的によるボーナス補正
        if scene_flow and scene_flow.episode_goal:
            goal = scene_flow.episode_goal.lower()
            for s_type, keywords in SCENE_KEYWORDS_WEIGHTED.items():
                if any(kw in goal for kw in keywords):
                    raw_probs[s_type] = raw_probs.get(s_type, 0.0) * 1.5

        # 4. Softmax再正規化
        norm_probs = _softmax(raw_probs)
        return sorted(norm_probs.items(), key=lambda x: x[1], reverse=True)
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_layer4_multiscene.py -o addopts="" --no-cov
  ```
- **合否基準**: 既存の Layer 4 テストがすべて Pass すること。

---

### Step 9: Layer 4 `trim` でのデュアル表記パースとカテゴリ優先度連動
- **目的**: デュアル表記された事実から元固有名詞を抽出し、ピン留めやアテンション判定を確実にヒットさせる。
- **対象ファイル**: [`src/services/compression/layer4_trimming.py`](file:///e:/hhh/src/services/compression/layer4_trimming.py)
- **編集内容**:
  `trim` 内で `fact_item.get("dual_name", fact_item.get("fact", ""))` を活用し、`entity` と `content` の両方からピン留め判定を厳密に実施。
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_layer4_multiscene.py -o addopts="" --no-cov
  ```
- **合否基準**: 全テストが Pass すること。

---

### Step 10: 文脈認識型シーン判定の単体テスト新規作成
- **目的**: 「戦闘直後の休息・作戦会議」において、キーワードだけで combat と誤認せず、正しく daily や political / general に判定されることを検証。
- **作成ファイル**: `tests/unit/test_context_aware_scene_detection.py`
- **コード内容**:
```python
import pytest
from src.services.compression.layer4_trimming import Layer4SceneTrimmer
from src.services.compression.models import SceneFlowHistory

def test_scene_context_aware_detection_handles_post_combat_meeting():
    trimmer = Layer4SceneTrimmer()
    # テキストには「魔王」「撃破」などの単語が含まれるが、主目的は「作戦会議・方針策定」
    plot = "魔王を討伐した後の対策会議を行う。今後の領地関税と防衛体制を協議する。"
    history = SceneFlowHistory(
        recent_scene_types=["combat"],
        episode_goal="戦後処理と政治的同盟交渉",
    )
    detected = trimmer.detect_scene_context_aware(plot, scene_flow=history)
    top_scene, prob = detected[0]
    
    # combat ではなく political または daily が優勢になること
    assert top_scene in ["political", "daily", "general"]
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_context_aware_scene_detection.py -o addopts="" --no-cov
  ```
- **合否基準**: 1 passed で完了すること。

---

### Step 11: 定量的評価指標モジュール `metrics.py` の新規実装
- **目的**: キャラクター保持率・伏線保持率・固有名詞保持率・総合整合性スコアを算出する純粋関数を実装。
- **作成ファイル**: `src/services/compression/metrics.py`
- **コード内容**:
```python
"""Quantitative consistency and retention metrics for context compression."""
from __future__ import annotations
import re
from src.services.compression.models import (
    CompressionQualityMetrics,
    ProtectedContext,
    TrimmedContextOutput,
)

def calculate_consistency_metrics(
    raw_text: str,
    trimmed_output: TrimmedContextOutput,
    protected_context: ProtectedContext | None = None,
    original_keywords: list[str] | None = None,
) -> CompressionQualityMetrics:
    """圧縮後テキストの情報保持率と整合性スコアを定量計算"""
    compressed = trimmed_output.compressed_text
    
    # 1. キャラクター保持率 (Protected active_characters)
    char_score = 1.0
    if protected_context and protected_context.active_characters:
        target_chars = [c for c in protected_context.active_characters if c in raw_text]
        if target_chars:
            hit = sum(1 for c in target_chars if c in compressed)
            char_score = hit / len(target_chars)

    # 2. 未回収伏線保持率 (Protected pending_foreshadowing_ids)
    foreshadow_score = 1.0
    if protected_context and protected_context.pending_foreshadowing_ids:
        target_fs = [f for f in protected_context.pending_foreshadowing_ids if f in raw_text]
        if target_fs:
            hit = sum(1 for f in target_fs if f in compressed)
            foreshadow_score = hit / len(target_fs)

    # 3. 固有名詞保持率 (カタカナ語および漢字複合語)
    proper_nouns = set(re.findall(r"[ァ-ンヴー]{3,}|[一-龯]{4,}", raw_text))
    noun_score = 1.0
    if proper_nouns:
        hit = sum(1 for n in proper_nouns if n in compressed)
        noun_score = hit / len(proper_nouns)

    # 4. セマンティック密度（トークンあたりの採用事実数）
    facts_count = len(trimmed_output.retained_entities)
    density_score = min(1.0, (facts_count * 10) / max(1, trimmed_output.token_count))

    # 5. 総合加重平均
    overall = (char_score * 0.35) + (foreshadow_score * 0.35) + (noun_score * 0.20) + (density_score * 0.10)

    return CompressionQualityMetrics(
        character_retention_score=round(char_score, 3),
        foreshadowing_retention_score=round(foreshadow_score, 3),
        proper_noun_retention_score=round(noun_score, 3),
        semantic_density_score=round(density_score, 3),
        overall_consistency_score=round(overall, 3),
    )
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.metrics import calculate_consistency_metrics; print('Step 11 OK')"
  ```
- **合否基準**: `Step 11 OK` と出力されること。

---

### Step 12: `FourLayerCompressor` へのシーン文脈伝搬とメトリクス組み込み
- **目的**: パイプライン実行時に自動で `CompressionQualityMetrics` を計算し、`CompressedContextResult.metrics` に格納する。
- **対象ファイル**:
  - [`src/services/compression/models.py`](file:///e:/hhh/src/services/compression/models.py)（`CompressedContextResult` に `metrics: CompressionQualityMetrics | None` を追加）
  - [`src/services/compression/compressor.py`](file:///e:/hhh/src/services/compression/compressor.py)
- **編集内容**:
  `compress` メソッドの引数に `scene_flow: SceneFlowHistory | None = None` を追加し、トリミング後に `calculate_consistency_metrics` を呼び出す。
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_compression_pipeline.py -o addopts="" --no-cov
  ```
- **合否基準**: 既存テストがすべて Pass すること。

---

### Step 13: `src/services/compression/__init__.py` の公開定義更新
- **目的**: 新設したモジュール・関数・クラスをパッケージ最上位からインポート可能にする。
- **対象ファイル**: [`src/services/compression/__init__.py`](file:///e:/hhh/src/services/compression/__init__.py)
- **編集内容**:
  `SceneFlowHistory`, `ReversibleEntityFact`, `CompressionQualityMetrics`, `calculate_consistency_metrics` をエクスポート。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression import SceneFlowHistory, CompressionQualityMetrics, calculate_consistency_metrics; print('Step 13 OK')"
  ```
- **合否基準**: `Step 13 OK` と出力されること。

---

### Step 14: `ContextBuilderAgent` へのシーン文脈連携
- **目的**: 小説生成オーケストレーターから直前シーン履歴を `compressor.compress` に渡す。
- **対象ファイル**: [`src/agents/context_builder_agent.py`](file:///e:/hhh/src/agents/context_builder_agent.py)
- **編集内容**:
  `scene_weights` 算出付近で `SceneFlowHistory(recent_scene_types=[...], episode_goal=...)` を構築してコンプレッサーに渡す。
- **検証コマンド**:
  ```powershell
  python -c "import src.agents.context_builder_agent; print('Step 14 Agent OK')"
  ```
- **合否基準**: エラーなくインポートが完了すること。

---

### Step 15: 定量的評価指標の単体テスト新規作成
- **目的**: 圧縮パイプライン実行時にキャラクターや伏線が保護され、高い整合性スコア（>= 0.85）を記録することを自動検証する。
- **作成ファイル**: `tests/unit/test_compression_consistency_metrics.py`
- **コード内容**:
```python
import pytest
from src.services.compression import FourLayerCompressor, ProtectedContext, SceneFlowHistory

def test_compression_pipeline_outputs_high_consistency_metrics():
    compressor = FourLayerCompressor()
    text = "勇者アレンは聖剣バルムンクを構えた。背後には魔法使いエレナが控えている。古の予言『月が紅く染まる時』の謎が迫る。"
    protected = ProtectedContext(
        active_characters=["アレン", "エレナ"],
        pending_foreshadowing_ids=["月が紅く染まる時"],
    )
    result = compressor.compress(text, protected_context=protected)
    
    assert result.metrics is not None
    assert result.metrics.character_retention_score == 1.0
    assert result.metrics.foreshadowing_retention_score == 1.0
    assert result.metrics.overall_consistency_score >= 0.80
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_compression_consistency_metrics.py -o addopts="" --no-cov
  ```
- **合否基準**: 1 passed で完了すること。

---

### Step 16: トークン削減率 vs 整合性スコア ベンチマークスクリプト作成
- **目的**: トークン予算（500〜3000 tokens）を変動させた際の「削減率」と「キャラ・伏線保持率」の相関を測定・可視化できるスクリプトを作成。
- **作成ファイル**: `tests/benchmarks/benchmark_consistency_and_reduction.py`
- **検証コマンド**:
  ```powershell
  python tests/benchmarks/benchmark_consistency_and_reduction.py
  ```
- **合否基準**: トークン予算ごとの削減率と整合性スコアが標準出力に表形式で出力されること。

---

### Step 17: 全圧縮関連テストの総合回帰検証
- **目的**: 18ステップを通じて、既存の Sudachi 解析、AGE 2-hop、動的タクソノミー、マルチシーン判定、および新規テストが全て通過することを確認。
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_compression_pipeline.py tests/unit/test_layer3_dynamic_abstraction.py tests/unit/test_layer3_reversible_abstraction.py tests/unit/test_layer4_multiscene.py tests/unit/test_context_aware_scene_detection.py tests/unit/test_compression_consistency_metrics.py -o addopts="" --no-cov
  ```
- **合否基準**: 対象テスト（全6ファイル、計50件以上）が **100% Passed（0 failed, 0 error）** で完了すること。

---

### Step 18: アーキテクチャ設計仕様書の作成
- **目的**: 本実装で実現した「可逆的デュアル抽象化」「文脈認識型シーン分類」「定量的整合性評価指標」の仕様・数式・API仕様をドキュメント化し、後続開発者やLLMが参照できるようにする。
- **作成ファイル**: `docs/architecture/COMPRESSION_REVERSIBLE_PIPELINE.md`
- **検証コマンド**:
  ```powershell
  python -c "import os; assert os.path.exists('docs/architecture/COMPRESSION_REVERSIBLE_PIPELINE.md'); print('Step 18 Docs OK')"
  ```
- **合否基準**: `Step 18 Docs OK` と出力されること。

---

## 🎯 期待成果物と完了基準
1. **成果物**:
   - デュアル抽象化表現（`抜刀・迅雷 [雷撃系近接スキル]`）の導入
   - 文脈認識型シーン分類器（`SceneFlowHistory` + マルコフ遷移）
   - 定量的整合性メトリクス算出エンジン（`metrics.py`）
   - 新規テスト 3 本およびベンチマークスクリプト 1 本
   - アーキテクチャ仕様書 `COMPRESSION_REVERSIBLE_PIPELINE.md`
2. **完了基準**:
   - [ ] 圧縮後コンテキスト内で主要キャラクターおよび未回収伏線保持率が 100% であること
   - [ ] シーン判定が直前シーン履歴を反映して滑らかに遷移すること
   - [ ] 圧縮品質メトリクスが全圧縮結果に自動付与されること
   - [ ] 全ユニットテストが All Green であること
