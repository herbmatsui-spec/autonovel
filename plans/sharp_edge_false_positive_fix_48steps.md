# 尖り保全 false positive 修正 + 意味的類似度拡張 実装計画（48ステップ）

**作成日**: 2026-07-10
**対象プロジェクト**: cR15 (覇権小説自動生成エンジン)
**目的**: 実LLMでの検証で判明した「尖り保全が常にfalse positiveを返す」問題の根本解決と、言い換えに対する耐性の追加
**関連ファイル**:
- `src/models/sharp_edge.py` — SharpEdgeSpec モデル
- `src/backend/sharp_edge_preserver.py` — 角保全検証器
- `src/agents/audit.py` — DeAIAuditor
- `src/backend/engine_critique.py` — CritiqueAgent
- `prompts/plotting.py` — SHARP_EDGE_PROPOSAL_TEMPLATE
- `config/settings.toml` — 設定 SSOT
- `src/models/db.py` — PlotDbModel
- `config/sharp_edge_vocabulary.py` — 角種定義

---

## 背景：実LLM検証で判明した問題

### 問題のメカニズム

実LLM（gemini-2.5-flash）が生成した尖りの `description` は以下の形式:

```json
{
  "edge_type": "protagonist_flaw",
  "description": "「深淵で得た力は、俺を新たな存在として蘇らせた」という記述から示唆される、主人公が人間性を失い、復讐の鬼と化してしまった側面。この欠陥は、読者の共感を誘い、..."
}
```

`check_edges_preserved` は `description[:20]` = `"「深淵で得た力は、" をキーとして after_content に字面一致を判定する。

生成された本文には「深淵で得た力」という字句は含まれているが、`「深淵で得た力` (先頭に全角スペースと括弧) は字面に存在せず、また説明文中の句点是も不一致のため **常に「削除された」と誤報告** される。

### 対策設計

| 層 | 対策 | 担当ステップ |
|---|---|---|
| 第1層: `key_phrase` 抽出 | プロンプトで「本文から直接引用した20文字以内の句」を `key_phrase` として分離要求。検証器はこれを最優先で使用 | Step 1-20 |
| 第2層: 意味的類似度 | 埋め込みベクトル（`text-embedding-004`）を使って `key_phrase` と本文のコサイン類似度を計算。閾値以上で「保持」と判定 | Step 21-42 |
| 第3層: フォールバック | 字面一致（`description[:20]`）は意味的判定で失敗した場合の最後のフォールバックとして残存 | Step 43-44 |

低性能LLMでも確実に実装できる粒度: **1ステップ = 1ファイル変更または1関数追加**、テスト必須、TDD（Red-Green-Refactor）前提。

---

# Part 1: key_phrase 追加による False Positive 修正（Step 1-24）

## Phase A: データモデル拡張（Step 1-10）

### Step 1: `SharpEdgeSpec` に `key_phrase` フィールド追加
**ファイル**: `src/models/sharp_edge.py`

**変更内容**:
```python
class SharpEdgeSpec(BaseModel):
    edge_type: str = Field(..., description="角の種類")
    description: str = Field(..., max_length=200, description="この角の内容（説明文）")
    key_phrase: str = Field(
        default="",
        max_length=20,
        description="本文から直接引用した20文字以内のキーフレーズ（品質化管理後も同一の字句が残ること）"
    )
    preserve_on_quality_polish: bool = Field(default=True)

    @field_validator("key_phrase")
    @classmethod
    def key_phrase_must_be_brief(cls, v: str) -> str:
        if v and len(v) > 20:
            raise ValueError("key_phrase は20文字以内にしてください")
        return v
```

**理由**: `key_phrase` を必須フィールド（デフォルト空文字）にすることで、提案時に未設定の場合はフォールバック処理が発動することを保証する。既存コードで `description` のみを使う箇所は後方互換を保つ。

### Step 2: SharpEdgeSpec の Pydantic バリデーター追加（Step 1 の補足テスト）
**ファイル**: `tests/test_sharp_edge.py`（既存に追記）

**テスト内容**:
- `key_phrase` が空文字 → OK（デフォルト許容）
- `key_phrase` が21文字以上 → `ValidationError`
- `key_phrase` が20文字ちょうど → OK
- `description` なしで `key_phrase` のみ → OK（description も必須なので ValidationError）

### Step 3: 角語彙ファイルへの `key_phrase` 要件メモ追加
**ファイル**: `config/sharp_edge_vocabulary.py`

**変更内容**:
```python
SHARP_EDGE_KEY_PHRASE_GUIDANCE: Dict[str, str] = {
    "ending_pullback": "本文中の結末に関する具体的描写（20文字以内）",
    "protagonist_flaw": "本文中の主人公欠陥を示す直接的表現（20文字以内）",
    "abnormal_dialogue": "本文から直接引用した異常セリフ（20文字以内）",
}
```

**理由**: プロンプト内でこの辞書を参照してLLMに「key_phrase は本文からの直接引用」を明示する。

### Step 4: DBスキーマ расширение（Plot.sharp_edges_json に key_phrase 追加）
**ファイル**: `alembic/versions/XXXX_add_sharp_edge_key_phrase.py`（新規）

**マイグレーションSQL**:
```sql
-- sharp_edges_json カラムは JSON 配列のまま。
-- 各要素に key_phrase フィールドが新增。既存データには空文字が自動的に入る。
-- マイグレーション不要（JSON 列はスキーマレスのため）。
-- しかし検証のため、明示的なマイグレーションファイルを作成する。
```

**備考**: `sharp_edges_json` はJSON配列をTEXT保存するスキーマレス列のため、application-levelでのBackward Compatibilityを保つ。Python側で `key_phrase` がない場合は空文字扱い。

### Step 5: PlotDbModel または PlotAnalytics への sharp_edges_key_phrases アクセス道路（Option）
**ファイル**: `src/models/db.py` の PlotDbModel 付近

**追加**: 便宜用に `def get_sharp_edge_phrases(plot) -> List[str]` を実装。`sharp_edges_json` をパースして `key_phrase` のみを列表。空文字は除外。

**理由**: 後の `check_edges_preserved` 改良で `key_phrase` だけを集めたリストを渡す簡便な方法を提供する。

### Step 6: 便宜関数 `resolve_sharp_edge_phrases(plot) -> List[str]` 追加
**ファイル**: `src/backend/engine_plot.py` または `src/backend/sharp_edge_preserver.py`

**内容**:
```python
def resolve_sharp_edge_phrases(plot: Optional[PlotDbModel]) -> List[str]:
    """Plot から key_phrase のみを抽出したリストを返す"""
    raw = getattr(plot, "sharp_edges_json", None) or getattr(plot, "sharp_edges", [])
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except Exception:
            return []
    else:
        data = raw
    phrases = []
    for item in (data if isinstance(data, list) else []):
        phrase = item.get("key_phrase", "").strip() if isinstance(item, dict) else ""
        if phrase:
            phrases.append(phrase)
    return phrases
```

### Step 7: Step 6 のユニットテスト作成
**ファイル**: `tests/test_sharp_edge_preserver.py`（既存に追記）

**テスト**:
- `key_phrase` が3件あるJSON → 3件のリストを返す
- `key_phrase` が空文字 only → 空リストを返す
- `key_phrase` がない（旧JSON） → 空リストを返す（後方互換）

---

## Phase B: プロンプトでの key_phrase 抽出（Step 8-14）

### Step 8: SHARP_EDGE_PROPOSAL_TEMPLATE 更新
**ファイル**: `prompts/plotting.py`

**現在のテンプレート**:
```
[
  {{"edge_type": "ending_pullback", "description": "...", "preserve_on_quality_polish": true}}
]
```

**新しいテンプレート**:
```
以下のプロット概要から、削ってはいけない角を3つ提案せよ。
角の種類は以下のいずれかで、JSON配列形式で返すこと。

- ending_pullback: 結末の引き方（期待を裏切る余韻のある終わり方）
- protagonist_flaw: 主人公の1つの欠陥（共感を誘う弱点）
- abnormal_dialogue: 異常なセリフ（キャラクターを際立たせる非日常的な発言）

【重要な約束事項】
- `description`: 角の内容を200文字以内で説明的に記述（読み手的解釈OK）
- `key_phrase`: 本文（プロット概要）から「そのまま 直接引用」した20文字以内の句。
  quality化管理で磨かれても、この句本身的は本文に残ること。
  必ず実際の本文から引用すること。説明文や要約は禁止。
  例: "「深淵で得た力" → description="深淵で得た力" の部分是不可

プロット概要:
{plot_summary}

出力形式:
[
  {{"edge_type": "ending_pullback", "description": "結末の具体的内容の説明（200字以内）", "key_phrase": "本文からの直接引用句（20文字以内）", "preserve_on_quality_polish": true}},
  ...
]
```

**理由**: 「説明的 description」vs「直接的 key_phrase」の二峰構造を明示。key_phrase は LLM の創作ではなく本文からという制約で低性能LLMでも失敗確率が低下。

### Step 9: PromptManager.build_sharp_edge_proposal_prompt に max_length 制約追加確認
**ファイル**: `prompts/manager.py` の `build_sharp_edge_proposal_prompt`

**変更**: 出力例テンプレート（Step 8参照）を更新し、`key_phrase: "20文字以内"` の制約を視覚的に明示。

### Step 10: 尖り提案応答パーサー強化: key_phrase 抽出 + バリデーション
**ファイル**: `src/backend/engine_plot.py` の `propose_sharp_edges`（既存関数）

**変更内容**:
```python
def _parse_sharp_edge_item(item: dict) -> Optional[SharpEdgeSpec]:
    """JSON要素から SharpEdgeSpec をパース。key_phrase がなければ空文字で補完。"""
    if not isinstance(item, dict):
        return None
    edge_type = item.get("edge_type", "")
    if edge_type not in SHARP_EDGE_TYPES:
        return None
    description = item.get("description", "").strip()
    key_phrase = item.get("key_phrase", "").strip()
    if len(key_phrase) > 20:
        # 20文字超えは警告ログのみ。超過分は切り捨て
        logger.warning(f"key_phraseが20字を超過: {key_phrase} → 先頭20字を使用")
        key_phrase = key_phrase[:20]
    try:
        return SharpEdgeSpec(
            edge_type=edge_type,
            description=description,
            key_phrase=key_phrase,
            preserve_on_quality_polish=item.get("preserve_on_quality_polish", True),
        )
    except ValidationError:
        return None
```

### Step 11: Step 10 のユニットテスト作成
**ファイル**: `tests/test_engine_sharp_edge_proposal.py`（既存に追記）

**テスト**:
- `key_phrase` が20字以内の正常ケース
- `key_phrase` が21字以上のケース → 先頭20字で補完
- `key_phrase` が完全に欠落しているケース → 空文字で補完（旧JSON後方互換）
- `key_phrase` が不正 edge_type → そのitemはスキップ（他は採用）

### Step 12: Step 10 の統合テスト（E2E）: プロット生成 → 尖り提案 → key_phrase 確認
**ファイル**: `tests/test_engine_sharp_edge_proposal.py`（既存 E2E テスト）

**テスト内容**:
- `build_sharp_edge_proposal_prompt` にプロット概要を入力
- モックLLMが正しい key_phrase を含むJSONを返した場合に `Plot.sharp_edges_json` に key_phrase 付きで保存されることを検証
- key_phrase が20字超の場合は切り捨てられることを検証

### Step 13: プロンプト例（few-shot）の追加
**ファイル**: `prompts/plotting.py` の SHARP_EDGE_PROPOSAL_TEMPLATE

**追加**: few-shot 示例をテンプレート末尾に追加:
```
【出力例】
[
  {"edge_type": "protagonist_flaw", "description": "優柔不断な性格が敵の陰謀を許す結果に", "key_phrase": "優柔不断な態度が裏目に", "preserve_on_quality_polish": true},
  ...
]
```

**理由**: 低性能LLM でも例示により key_phrase=直接引用 の形式を確実に実現。

### Step 14: Step 13 のテスト（few-shot がプロンプトに含まれているか）
**ファイル**: `tests/test_sharp_edge_prompt.py`

**変更**: `build_sharp_edge_proposal_prompt` で生成されたプロンプトに `"key_phrase"` と `"20文字以内"` の文字列が含まれることを検証。

---

## Phase C: check_edges_preserved の改善（Step 15-20）

### Step 15: check_edges_preserved 改善: key_phrase 最優先、description[:20] フォールバック
**ファイル**: `src/backend/sharp_edge_preserver.py`

**新しいロジック**:
```python
def check_edges_preserved(before_content: str, after_content: str, edges: List[SharpEdgeSpec]) -> List[SharpEdgeSpec]:
    """
    品質向上前後のコンテンツを比較し、削除された角を検出する。

    優先順位:
    1. edge.key_phrase (優先) — after_content に key_phrase が字面一致で含まれるか
    2. edge.description[:20] (フォールバック) — description の先頭20字で判定

    削除された edge のリストを返す（空リスト = 全角保持）。
    """
    if not edges:
        return []

    lost: List[SharpEdgeSpec] = []
    after_lower = after_content.lower()

    for edge in edges:
        preserved = False

        # Priority 1: key_phrase (the primary check)
        key_phrase = edge.key_phrase.strip() if edge.key_phrase else ""
        if key_phrase:
            if key_phrase.lower() in after_lower:
                preserved = True
                logger.debug("key_phraseで保持確認: %s (%s)", edge.edge_type, key_phrase)

        # Priority 2: description[:20] fallback (legacy)
        if not preserved:
            desc_phrase = edge.description.strip()[:20].lower()
            if desc_phrase and desc_phrase in after_lower:
                preserved = True
                logger.debug("description[:20]で保持確認 (key_phraseなし): %s (%s)", edge.edge_type, desc_phrase)

        if not preserved:
            lost.append(edge)
            logger.debug("角が削除されました: %s", edge.edge_type)

    return lost
```

**理由**: key_phrase がある場合はそれを使い、なければ従来の description[:20] にフォールバック。后方互換を保ちつつ、改善を段階的に適用。

### Step 16: Step 15 の単体テスト（key_phrase を使用した場合）
**ファイル**: `tests/test_sharp_edge_preserver.py`（既存に追記）

**テスト**:
```python
def test_key_phrase_preserved(self):
    edges = [SharpEdgeSpec(edge_type="protagonist_flaw", description="長い説明文", key_phrase="深淵で得た力")]
    after = "深淵で得た力 が彼を新たな存在として蘇らせた。"  # key_phrase を含む
    result = check_edges_preserved("before", after, edges)
    assert result == []  # 保持された

def test_key_phrase_removed(self):
    edges = [SharpEdgeSpec(edge_type="protagonist_flaw", description="長い説明文", key_phrase="深淵で得た力")]
    after = "彼は新たな力を得た。"  # key_phrase なし
    result = check_edges_preserved("before", after, edges)
    assert len(result) == 1

def test_key_phrase_falls_back_to_description(self):
    # key_phrase が空の場合、description[:20] にフォールバック
    edges = [SharpEdgeSpec(edge_type="abnormal_dialogue", description="『退屈だね』", key_phrase="")]
    after = "before after 『退屈だね』 异常なセリフ"
    result = check_edges_preserved("before", after, edges)
    assert result == []  # description[:20] = "『退屈だね』" で一致

def test_key_phrase_priority_over_description(self):
    # description[:20] が一致しても、key_phrase が異なる場合は key_phrase が優先
    edges = [SharpEdgeSpec(edge_type="ending_pullback", description="結末は唐突に終わった", key_phrase="突然の幕切れ")]
    after = "突然の幕切れで物語が終わった"  # key_phrase OK、description[:20]="結末は唐突に" はNG
    result = check_edges_preserved("before", after, edges)
    assert result == []  # key_phrase で一致
```

### Step 17: DeAIAuditor.audit の edge 判定部分を logger.debug で詳細化
**ファイル**: `src/agents/audit.py` の DeAIAuditor.audit 内

**変更**: `check_edges_preserved` の結果をログ出力する際、 lost でなく preserved の件数もログに追加して、可観測性を向上。

### Step 18: Step 17 のテスト（logger出力の検証）
**ファイル**: `tests/test_deai_auditor_edges.py`（既存に追記）

**変更**: `caplog` を使って `audit` 呼び出し後のログに preserved/edgeloss が記録されていることを検証。

### Step 19: 全 Phase 1-3 統合 E2E テスト（key_phrase 込み）
**ファイル**: `tests/test_phase4to5_e2e.py`（既存テストを key_phrase 対応に更新）

**更新内容**:
- 尖り提案で `key_phrase` を含むJSONを返すモックに更新
- 「key_phrase が保持された場合 → passed=True」を明示テスト
- 「key_phrase が削除された場合 → passed=False」を明示テスト
- 「key_phrase なし + description[:20] フォールバック → passed=True」（後方互換）

### Step 20: ドキュメント更新: `config/sharp_edge_vocabulary.py` の docstring 更新
**ファイル**: `config/sharp_edge_vocabulary.py`

**追加 docstring**:
```
key_phrase: プロットまたは本文から「直接引用」した20文字以内の句。
            description よりも優先して check_edges_preserved で使用される。
            LLMが説明的文ではなく直接引用を生成することを強制するため、
            プロンプトテンプレートで明示的に指引する。
```

---

# Part 2: 意味的類似度による尖り保全（Step 21-42）

## Phase D: 埋め込みインフラ確認（Step 21-24）

### Step 21: 既存の埋め込みインフラ調査確認
**ファイル**: `src/services/semantic_cache.py`, `src/backend/engine_style_rag.py`, `src/services/vector_store.py`

**調査項目**:
- `_get_embedding(text: str) -> List[float]` の実装詳細（キャッシュの有無）
- `DefaultVectorStore` の `add_documents` / `search` API
- `MODEL_EMBEDDING = "text-embedding-004"` (config/base.py) の существование
- `container.vector_store` が null の場合のGraceful degradation

**結果**: `SemanticCacheManager._get_embedding` が実装済み。`vector_store` が None でも LRU キャッシュのみにフォールバックする設計のため、意味的判定は `vector_store` が None でも動作する（初回のみEmbedding計算コストが発生）。

### Step 22: SemanticCacheManager のエッジ保全用ヘルパーメソッド追加
**ファイル**: `src/services/semantic_cache.py`

**追加内容**:
```python
async def compute_similarity(self, text1: str, text2: str) -> float:
    """
    2つのテキスト間のコサイン類似度（0.0-1.0）を計算する。
    埋め込みベクトル取得コスト高いため、入力テキストが同一の場合は 1.0 を直接返す最適化を含む。
    """
    if text1 == text2:
        return 1.0
    vec1 = await self._get_embedding(text1)
    vec2 = await self._get_embedding(text2)
    norm1 = math.sqrt(sum(v * v for v in vec1))
    norm2 = math.sqrt(sum(v * v for v in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    return dot / (norm1 * norm2)
```

**理由**: `SemanticCacheManager` は既存の `embedding_model` と `_get_embedding` を持つ。このクラスに `compute_similarity` メソッドを追加すれば DI を変更不要。`math.sqrt` のため `import math` を追加。

### Step 23: Step 22 のユニットテスト
**ファイル**: `tests/test_semantic_cache.py`（既存、または `tests/test_similarity.py` 新規）

**テスト**:
- 同一テキスト → 1.0
- 完全に異なるテキスト → > 0.0 の任意値（計算確認）
- 空文字列 → 0.0（norm=0 チェック）
- キャッシュが利く場合（2回目に同じテキスト）→ same result, 高速

### Step 24: SemanticCacheManager が DI コンテナに接続されているか確認
**ファイル**: `src/core/container.py`, `src/services/semantic_cache.py`

**確認**: `container.semantic_cache` Provider は既存（`SemanticCacheManager` インスタンスを生成）。これを `SemanticEdgePreserver` に注入する準備。

---

## Phase E: SemanticEdgePreserver 実装（Step 25-36）

### Step 25: SemanticEdgePreserver クラス設計
**ファイル**: `src/backend/sharp_edge_preserver.py`（SharpEdgePreserver をリネーム・拡張）

**設計思想**:
- 低性能LLM でも確実に動作: string match (key_phrase) → 意味的類似度 → フォールバック の3層
- `SemanticCacheManager` を DI するため、なければ string-only mode にGraceful degradation
- 閾値は `config/settings.toml` の `[edge_preservation]` セクションで管理

### Step 26: SemanticEdgePreserver 基本骨組
**ファイル**: `src/backend/sharp_edge_preserver.py`

**追加内容**:
```python
import math
from typing import List, Optional, Tuple

class SemanticEdgePreserver:
    """
    意味的類似度を使った尖り保全検証器。
    check_edges_preserved + 意味的類似度の2段構成。
    """
    def __init__(
        self,
        semantic_cache=None,  # SemanticCacheManager or None
        similarity_threshold: float = 0.75,
        enable_semantic: bool = True,
    ):
        self.semantic_cache = semantic_cache
        self.similarity_threshold = similarity_threshold
        self.enable_semantic = enable_semantic and (semantic_cache is not None)

    def check_string_only(self, after_content: str, edges: List[SharpEdgeSpec]) -> List[SharpEdgeSpec]:
        """Step 15 の文字列一致ロジック（これ以上踏み込まない）"""
        return check_edges_preserved("", after_content, edges)

    async def check_edges_preserved(
        self,
        before_content: str,
        after_content: str,
        edges: List[SharpEdgeSpec],
    ) -> Tuple[List[SharpEdgeSpec], List[SharpEdgeSpec]]:
        """
        文字列一致 + 意味的類似度の2段階で削除された角を検出。

        Returns: (lost_by_string: List, lost_by_semantic: List)
        - string で失われたが semantic で保持された → semantic recovery
        - semantic でも失われた → 本当に削除された
        """
        if not edges:
            return [], []
        if not self.enable_semantic:
            lost = self.check_string_only(after_content, edges)
            return lost, lost  # 両方同じ

        # Phase 1: string match
        string_lost = self.check_string_only(after_content, edges)
        preserved_edges = [e for e in edges if e not in string_lost]

        # Phase 2: semantic check on string-lost candidates
        semantic_lost = []
        for edge in string_lost:
            similarity = await self._compute_similarity(before_content, after_content, edge)
            if similarity < self.similarity_threshold:
                semantic_lost.append(edge)
                logger.debug("意味的類似度で削除検出: %s (similarity=%.2f < %.2f)",
                              edge.edge_type, similarity, self.similarity_threshold)
            else:
                logger.debug("意味的類似度で保持確認: %s (similarity=%.2f >= %.2f)",
                             edge.edge_type, similarity, self.similarity_threshold)

        return semantic_lost, string_lost  # semantic_lost は本当に失われた

    async def _compute_similarity(
        self,
        before_content: str,
        after_content: str,
        edge: SharpEdgeSpec,
    ) -> float:
        """key_phrase と本文の間の類似度を計算する。"""
        if not self.semantic_cache:
            return 0.0
        key_phrase = edge.key_phrase.strip() or edge.description.strip()[:20]
        return await self.semantic_cache.compute_similarity(
            key_phrase,
            after_content,
        )
```

### Step 27: Step 26 の非同期対応 + asyncio.run でのテスト確認
**ファイル**: `tests/test_sharp_edge_preserver.py`（既存に追記）

**テスト**:
- `semantic_cache=None` → string-only mode にgraceful degradation
- `semantic_cache=Mock` → 非同期 simulate

### Step 28: config/settings.toml に意味的類似度設定をSSOT追加
**ファイル**: `config/settings.toml`

**追加セクション**:
```toml
[edge_preservation]
similarity_threshold = 0.75   # コサイン類似度閾値 (0.0-1.0)
enable_semantic = true         # 意味的判定の有効/無効
semantic_fallback_string = true  # 意味的判定失败时是否回退到字符串一致
```

### Step 29: GlobalConfigModel (schemas/config.py) に edge_preservation 設定追加
**ファイル**: `schemas/config.py`（既存 GlobalConfigModel に Field 追加）

**追加 Field**:
```python
similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
enable_semantic_edge_preservation: bool = Field(default=True)
```

### Step 30: Step 29 のバリデーションテスト
**ファイル**: `tests/test_config.py`（既存）

**テスト**:
- 閾値 0.75 → OK
- 閾値 -0.1 → ValidationError
- 閾値 1.5 → ValidationError
- enable_semantic = False → OK

### Step 31: SemanticEdgePreserver を DI コンテナに追加
**ファイル**: `src/core/container.py`

**追加 Provider**:
```python
edge_preserver = providers.Singleton(
    SemanticEdgePreserver,
    semantic_cache=semantic_cache,       # container.semantic_cache() から
    similarity_threshold=0.75,            # 後で ProjectContext.get_setting 経由で上書き
    enable_semantic=True,
)
```

### Step 32: DeAIAuditor に SemanticEdgePreserver を注入
**ファイル**: `src/agents/audit.py` の DeAIAuditor.__init__

**変更**:
```python
class DeAIAuditor:
    def __init__(
        self, repo=None, llm: LLMService = None, prompt_manager: Any = None,
        edge_preserver=None,  # 新規オプションパラメータ
        *args, **kwargs
    ):
        self.edge_preserver = edge_preserver  # None の場合は check_edges_preserved を直接呼ぶ後方互換
```

### Step 33: DeAIAuditor.audit の semantic 統合
**ファイル**: `src/agents/audit.py` の DeAIAuditor.audit

**変更内容**:
```python
async def audit(self, content: str, before_content: Optional[str] = None,
                edges: Optional[List[SharpEdgeSpec]] = None,
                emotional_hook: Optional[Any] = None) -> Tuple[bool, str]:
    if edges:
        if self.edge_preserver:
            # Semantic mode
            semantic_lost, string_lost = await self.edge_preserver.check_edges_preserved(
                before_content or "", content, edges
            )
            if semantic_lost:
                lost_types = ", ".join(e.edge_type for e in semantic_lost)
                msg = f"以下の角が削られました（意味的類似度判定）: {lost_types}"
                if string_lost and len(string_lost) > len(semantic_lost):
                    preserved = [e.edge_type for e in edges if e not in semantic_lost]
                    msg += f"\n(字面では失われたが意味的に保持された: {preserved})"
                return False, msg
        else:
            # Legacy string-only mode (後方互換)
            lost = check_edges_preserved(before_content or "", content, edges)
            if lost:
                lost_types = ", ".join(e.edge_type for e in lost)
                return False, f"以下の角が削られました: {lost_types}"
```

### Step 34: Step 33 のユニットテスト
**ファイル**: `tests/test_deai_auditor_edges.py`（既存に semantic 版を追記）

**テスト**:
- `edge_preserver=None` → 従来の check_edges_preserved (string-only) を使用
- `edge_preserver=SemanticEdgePreserver` → 意味的類似度が発動
- string match で保持 + semantic で保持 → `passed=True`
- string match で削除 + semantic で保持 → `passed=True`（意味的 recovery）← **新しい動作**
- string match で削除 + semantic で削除 → `passed=False`（本当の削除）
- `semantic_cache=None` → string-only mode にgraceful degradation

### Step 35: CritiqueAgent.run_iterative_gap_analysis に semantic edge 保全統合
**ファイル**: `src/backend/engine_critique.py`

**変更箇所**: `run_iterative_gap_analysis` 内で `check_edges_preserved` を呼んでいる箇所を `edge_preserver.check_edges_preserved` に置換。（`engine_critique.py` の先頭で `from src.backend.sharp_edge_preserver import SemanticEdgePreserver` を追加し、`self.edge_preserver` を DI 経由または `SemanticEdgePreserver(semantic_cache=None)` でインスタンス化）

### Step 36: Step 35 のテスト（CritiqueAgent edge rejection）
**ファイル**: `tests/test_critique_edge_rejection.py`（既存）

**変更**: Mockの `edge_preserver` を注入して、semantic 模式下での edge rejection を検証。

---

## Phase F: LLM非依存の高速類似度代替手段（Step 37-40）

### Step 37: 軽量N-gram類似度の実装（Embeddingコスト代替）
**ファイル**: `src/backend/sharp_edge_preserver.py`（ユーティリティ関数追加）

**理由**: 低性能LLM でもEmbedding API呼び出しコスト・レイテンシを避けたい場合がある。bi-gram ベースの Jaccard 係数で代用可能か確認。

**実装**:
```python
def compute_ngram_similarity(text1: str, text2: str, n: int = 2) -> float:
    """
    bi-gram Jaccard類似度による高速類似度計算。
    embedding不要。0.0-1.0 を返す。
    低性能LLM環境でのフォールバック或いは pre-filter として使用可能。
    """
    if not text1 or not text2:
        return 0.0

    def get_ngrams(s: str, n: int):
        s = s.replace(" ", "").lower()
        return set(s[i:i+n] for i in range(len(s) - n + 1))

    grams1 = get_ngrams(text1, n)
    grams2 = get_ngrams(text2, n)
    if not grams1 or not grams2:
        return 0.0
    intersection = len(grams1 & grams2)
    union = len(grams1 | grams2)
    return intersection / union if union > 0 else 0.0
```

### Step 38: Step 37 のユニットテスト
**ファイル**: `tests/test_sharp_edge_preserver.py`

**テスト**:
- 同一テキスト → 1.0
- 無関係テキスト → 低スコア（0.0-0.2 程度）
- 部分的に共有表現 → 中間スコア（0.3-0.7 程度）

### Step 39: SemanticEdgePreserver に N-gram フォールバック追加
**ファイル**: `src/backend/sharp_edge_preserver.py`

**変更**: `SemanticEdgePreserver` のコンストラクタに `use_ngram_fallback: bool = False` を追加。semantic_cache が None でも N-gram similarity が有効なら字面判定を補完する。

```python
async def _compute_similarity(self, ...):
    # priority: embedding > N-gram > 0.0
    try:
        if self.semantic_cache:
            return await self.semantic_cache.compute_similarity(...)
    except Exception:
        pass
    if self.use_ngram_fallback:
        return compute_ngram_similarity(key_phrase, after_content)
    return 0.0
```

### Step 40: Step 39 のテスト
**ファイル**: `tests/test_sharp_edge_preserver.py`

**テスト**:
- `semantic_cache=None, use_ngram_fallback=False` → similarity = 0.0
- `semantic_cache=None, use_ngram_fallback=True` → N-gram score を返す

---

## Phase G: 統合・設定・テスト（Step 41-48）

### Step 41: `check_edges_preserved` の呼び出し元全箇所調査と置換
**ファイル**: `src/agents/audit.py`, `src/backend/engine_critique.py`, `tests/` 内全ファイル

**調査コマンド**:
```bash
rg "check_edges_preserved" --type py -l
```

**置換方針**:
- `src/agents/audit.py` DeAIAuditor: Step 33 で対応済み
- `src/backend/engine_critique.py` CritiqueAgent: Step 35 で対応済み
- テストファイル: `check_edges_preserved` の直接呼出は従来通り（後方互換）、必要に応じて semantic 版テストを追加

### Step 42: TDD による全角保全パイプライン E2E テスト
**ファイル**: `tests/test_full_balance_pipeline_e2e.py`（既存テストを semantic 版に更新）

**更新内容**:
- Phase 4 E2E: 尖り提案に key_phrase を含む JSON を返すモックに更新
- Phase 5 E2E: `DeAIAuditor` + `edge_preserver` (semantic) を使い、「key_phrase は保持されたが説明文は変わった」ケースで `passed=True` を返すことを検証
- Phase 5 E2E: 意味的に削除された場合 → `passed=False` を検証

### Step 43: ruff/mypy 静的解析実行
**ファイル**: 全変更箇所

**実行**:
```bash
ruff check src/models/sharp_edge.py src/backend/sharp_edge_preserver.py src/agents/audit.py src/backend/engine_critique.py
mypy src/models/sharp_edge.py src/backend/sharp_edge_preserver.py
```

**修正**: エラー0 を目指す。型ヒント不足があれば追加。

### Step 44: 設定ドキュメント更新
**ファイル**: `config/settings.toml` に `[edge_preservation]` セクション説明追記、`plans/quality_entertainment_balance_72steps.md` に本48ステップを Phase 9 として追記。

### Step 45: Step 43 の CI テスト自動実行確認
**ファイル**: `pytest.ini` 確認 + `python -m pytest tests/test_sharp_edge_preserver.py tests/test_deai_auditor_edges.py tests/test_critique_edge_rejection.py tests/test_phase4to5_e2e.py tests/test_full_balance_pipeline_e2e.py -v`

**期待**: 全テスト PASS

### Step 46: 低性能LLM（gemma-4-31b-it）での key_phrase 抽出精度確認
**ファイル**: `scratch/test_key_phrase_extraction.py`（新規）

**テスト**: `PromptManager.build_sharp_edge_proposal_prompt` を呼び出し、モックではなく実際のLLM（低性能モデル）で key_phrase を生成させ、3件中2件以上が20文字以内の直接引用であることを確認。

### Step 47: 実LLMによる最終統合検証（balance_verify.py 更新版）
**ファイル**: `balance_verify.py`（既存スクリプトを更新）

**更新内容**:
1. 生成された尖りに `key_phrase` が含まれていることをassert
2. DeAIAuditor.audit(preserved_case) が `passed=True` を返すことを確認（**Step 44の目標**）
3. 意味的類似度による recovery（stringで失われたがsemanticで保持）を実演
4. 閾値変更（0.6, 0.8）を試して感度を検証

### Step 48: Phase 9完了レポート + 既存 BALANCE_ADJUSTMENT_VERIFICATION_REPORT.md 更新
**ファイル**: `BALANCE_ADJUSTMENT_VERIFICATION_REPORT.md`

**内容**:
- Part 1 の false positive 問題が修正されたことを実LLMで再検証し、passed=True が確認できた旨を明記
- Part 2 の意味的類似度が string match を補完し、"言い換えによる誤検出" に対応できることの検証結果
- 性能への影響を記録（Embedding API呼び出しコスト、初回遅延）

---

## 完了定義（Definition of Done）

- [ ] 全48ステップが `pytest` で PASS
- [ ] `ruff` / `mypy` エラー 0
- [ ] 実LLM（gemini-2.5-flash）での最終検証で `DeAIAuditor.audit(preserved_content)` → `passed=True` が確認できること
- [ ] 意味的類似度による "言い換え耐性" が実例で確認できること
- [ ] 旧テスト（key_phrase なし JSON）が後方互換で動作すること

---

## 低性能LLM でも確実に動作するための設計担保

| 設計方針 | 実装箇所 | 効果 |
|---|---|---|
| 1ステップ＝1ファイル/1関数 | 全Step | cognitive load 最小化 |
| プロンプトでの直接引用强制 | Step 8, 13 | key_phrase が本文字句になることをLLMに頑なに指示 |
| key_phrase のフォールバック | Step 15 | description[:20] で後方互換保持 |
| semantic判定のGraceful degradation | Step 26, 31 | vector_store/semantic_cache が None でも動作継続 |
| N-gram 代替手段 | Step 37-40 | Embedding API障害時も類似度計算可能 |
| TDD（Red-Green-Refactor） | 各Step のテスト | リグレッション防止 |