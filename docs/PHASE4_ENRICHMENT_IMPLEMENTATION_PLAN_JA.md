# フェーズ4: マルチモーダルエンリッチメント統合 - 詳細実装計画書（72ステップ）

---

## カテゴリ A: 基盤・設定（ステップ 1-6）

### ステップ 1: エンリッチメント設定ファイル作成
- **ファイル**: `config/enrichment.yaml`
- **変更内容**: 機能フラグ、重み、閾値を含む新規設定作成
- **仕様**:
```yaml
enrichment:
  enabled: false  # 機能フラグ（安全ロールアウト用）
  trivia_insertion:
    enabled: true
    max_insertions_per_chapter: 5
    relevance_threshold: 0.7
    sources: ["world_bible", "historical_facts", "cultural_trivia"]
  citation_attachment:
    enabled: true
    style: "footnote"  # footnote, bracket, endnote
    max_citations_per_chapter: 10
    source_priority: ["world_bible", "canon_material", "historical_records"]
  sensory_expansion:
    enabled: true
    target_emotions: ["sadness", "anger", "fear", "joy", "surprise", "disgust"]
    expansion_ratio: 2.5  # 抽象→具体の倍率
    show_dont_tell: true
  multimedia_scenarios:
    enabled: true
    formats: ["manga_script", "radio_drama", "anime_storyboard", "live_action_shots"]
    trigger_scenes: ["climax", "battle", "emotional_peak", "revelation", "romance"]
  token_budget:
    max_enrichment_tokens: 1500
    reserve_for_audit: 500
```
- **テスト**: `python -c "import yaml; yaml.safe_load(open('config/enrichment.yaml'))"`

### ステップ 2: プロンプトテンプレートディレクトリ作成
- **ファイル**: `prompts/enrichment/__init__.py`
- **変更内容**: パッケージ初期化ファイル作成
- **仕様**: `__all__ = []` のみの空ファイル

### ステップ 3: トリビア挿入プロンプト作成
- **ファイル**: `prompts/enrichment/trivia_insertion.py`
- **変更内容**: トリビアフィルタリング・挿入用プロンプトテンプレート作成
- **仕様**:
```python
TRIVIA_INSERTION_PROMPT = """
以下の本文に、世界観設定から関連性の高い雑学・トリビアを自然に組み込んでください。

【本文】
{original_text}

【候補トリビア一覧】
{trivia_candidates}

【制約】
- 最大 {max_insertions} 箇所まで挿入
- 文体・視点・時制を完全に維持
- 会話文中なら会話として、地の文ならナレーションとして自然に
- 「歴史的には…」等の説明調にならないよう注意
- 関連度 {relevance_threshold} 以上のみ採用

【出力形式】JSON:
{{
  "enriched_text": "組み込み済み本文",
  "insertions": [
    {{"position": 123, "original": "...", "enriched": "...", "trivia_source": "..."}}
  ]
}}
"""
```
- **テスト**: `python -c "from prompts.enrichment.trivia_insertion import TRIVIA_INSERTION_PROMPT; print(len(TRIVIA_INSERTION_PROMPT))"`

### ステップ 4: 引用付与プロンプト作成
- **ファイル**: `prompts/enrichment/citation_attachment.py`
- **変更内容**: ソース引用生成用プロンプト作成
- **仕様**: 同様の構造で、脚注マーカーと文献リストを出力

### ステップ 5: 感覚拡充プロンプト作成
- **ファイル**: `prompts/enrichment/sensory_expansion.py`
- **変更内容**: Show-Don't-Tell 感覚書き換え用プロンプト作成
- **仕様**: 抽象的感情を検出し、五感ベースの具体描写に展開

### ステップ 6: マルチメディアシナリオプロンプト作成
- **ファイル**: `prompts/enrichment/multimedia_scenarios.py`
- **変更内容**: 派生フォーマット生成用プロンプト作成
- **仕様**: マンガ/ラジオ/アニメ形式の構造化JSONを出力

---

## カテゴリ B: EnrichmentAgent コア（ステップ 7-12）

### ステップ 7: EnrichmentAgent 基底クラス作成
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 新規ファイル、`EnrichmentAgent(SkillAgent)` に `__init__`、依存関数を定義
- **仕様**:
```python
class EnrichmentAgent(SkillAgent):
    def __init__(self, repo=None, llm=None, style_rag=None, rag_prefetch=None,
                 rag_service=None, prompt_manager=None, event_bus=None):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, 
                         rag_prefetch=rag_prefetch, event_bus=event_bus)
        self.rag_service = rag_service
        self.prompt_manager = prompt_manager
```
- **テスト**: `python -c "from src.agents.enrichment_agent import EnrichmentAgent; print('OK')"`

### ステップ 8: execute() メインエントリーポイント実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `async def execute(self, ctx: AgentContext) -> AgentResult` 追加
- **仕様**:
  - 入力: `ctx.artifacts["drafted_text"]`, `ctx.artifacts["writing_context"]`
  - 出力: `enriched_text`, `enrichment_metadata`
  - 4つのサブメソッドを順次呼び出し
  - `enrichment.started` / `enrichment.completed` イベント発行
- **テスト**: モックLLMでエンリッチメント済みテキスト返却を検証

### ステップ 9: _enrich_with_trivia() メソッド実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: トリビア挿入用プライベートメソッド
- **仕様**:
  - GraphRAG でシーン関連エンティティ/事実をクエリ
  - `TRIVIA_INSERTION_PROMPT` で LLM フィルタリング
  - 自然な位置（段落境界等）に挿入
  - `(enriched_text, insertion_metadata)` を返却
- **テスト**: モックGraphRAG+LLMで挿入数 ≤ 設定値を検証

### ステップ 10: _attach_citations() メソッド実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 引用付与用プライベートメソッド
- **仕様**:
  - テキスト内の事実記述を World Bible ソースにマッピング
  - 脚注マーカー `[^1]` と文献リスト生成
  - `citation_map: {marker: source_info}` を維持
- **テスト**: 脚注数、マーカー位置の妥当性を検証

### ステップ 11: _expand_sensory_details() メソッド実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 感覚拡充用プライベートメソッド
- **仕様**:
  - 抽象的感情フレーズ検出（正規表現 + LLM）
  - 各フレーズに対して五感具体描写生成
  - 文脈フローを保ちながら置換
- **テスト**: 入力「彼は悲しかった」→ 出力に涙/温度/音/触覚/臭いが含まれる

### ステップ 12: _generate_multimedia_scenarios() メソッド実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: マルチメディアシナリオ生成用プライベートメソッド
- **仕様**:
  - トリガーシーン（クライマックス、バトル等）をキーワード/構造で特定
  - 各シーンでマンガ台本/ラジオドラマ/絵コンテ JSON をレンダリング
  - `enrichment_metadata["multimedia"]` に格納
- **テスト**: トリガーシーンで4形式すべてが存在することを検証

---

## カテゴリ C: トリビア挿入（ステップ 13-18）

### ステップ 13: トリビア用 GraphRAG クエリヘルパー追加
- **ファイル**: `src/services/rag_service.py`
- **変更内容**: `async def query_trivia_candidates(self, session, scene_context, entities, limit=20)` 追加
- **仕様**: 「トリビア価値ある」事実（歴史、文化、アイテム伝承）をハイブリッド検索
- **テスト**: `{fact, source, relevance_score}` のリストを返却

### ステップ 14: トリビア関連度スコアリング実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_score_trivia_relevance(trivia, scene_context)` メソッド追加
- **仕様**: コサイン類似度 + キーワード重なり + エンティティマッチ
- **テスト**: 関連トリビア > 0.7、無関連 < 0.3

### ステップ 15: 自然な挿入ポイント検出実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_find_insertion_points(text, max_points)` メソッド追加
- **仕様**: 段落区切り、シーン遷移、会話のポーズ
- **テスト**: 文字インデックスリスト返却、個数 ≤ max_points

### ステップ 16: トリビア→テキスト書き換え実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_rewrite_trivia_for_context(trivia, surrounding_text, pov)` メソッド追加
- **仕様**: 文脈ウィンドウ ±200文字で LLM 呼び出し、視点/時制維持
- **テスト**: スタイル整合性チェック通過

### ステップ 17: トリビア挿入メタデータ追跡追加
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `enrichment_metadata["trivia"] = [{"source", "position", "original", "enriched", "relevance"}]` 構造化
- **仕様**: 各挿入の完全監査証跡
- **テスト**: メタデータ長 = 挿入数

### ステップ 18: トリビア トークン予算強制実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_estimate_tokens(enriched_text) - _estimate_tokens(original) ≤ budget` チェック
- **仕様**: 予算超過時は関連度低い挿入から切り捨て
- **テスト**: トークン差分が `config.enrichment.token_budget.max_enrichment_tokens` 以内

---

## カテゴリ D: 引用付与（ステップ 19-24）

### ステップ 19: World Bible ソース索引追加
- **ファイル**: `src/services/rag_service.py`
- **変更内容**: `async def index_bible_sources(self, session, book_id)` 追加
- **仕様**: 検索可能マップ作成: `claim_pattern → source_ref`
- **テスト**: 既知事実で正しいソース返却

### ステップ 20: 事実記述抽出実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_extract_factual_claims(text)` メソッド追加
- **仕様**: LLM + 正規表現で検証可能文（日付、名前、ルール、メカニクス）検出
- **テスト**: テストコーパスの手動アノテーション ≥80% 抽出

### ステップ 21: ソースマッチング実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_match_claims_to_sources(claims, bible_index)` メソッド追加
- **仕様**: セマンティック類似度 + エンティティマッチ、閾値 0.75
- **テスト**: 既知 claim-source ペアが正しくマッチ

### ステップ 22: 脚注マーカー挿入実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_insert_footnote_markers(text, claim_source_pairs)` メソッド追加
- **仕様**: 記述文末に `[^n]` 挿入、文献リスト収集
- **テスト**: マーカーが文構造を壊さない、文献リスト完全

### ステップ 23: 引用スタイルフォーマット実装
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `_format_citations(bibliography, style)` メソッド追加
- **仕様**: 設定に従い `footnote`/`bracket`/`endnote` 対応
- **テスト**: 各スタイル正しくレンダリング

### ステップ 24: 引用メタデータ追跡追加
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `enrichment_metadata["citations"] = [{"marker", "claim", "source", "style"}]`
- **テスト**: 往復変換: text + metadata → 元の claim 回復可能

---

## カテゴリ E: 感覚拡充（ステップ 25-30）

### ステップ 25: 感情検出モジュール作成
- **ファイル**: `src/agents/enrichment/sensory.py` (新規)
- **変更内容**: `detect_abstract_emotions(text) → List[EmotionSpan]` 新規モジュール
- **仕様**: `EmotionSpan = {start, end, emotion, intensity, abstract_phrase}`
- **テスト**: 「悲しかった」「怒りが込み上げた」「恐怖で震えた」等を検出

### ステップ 26: 感覚マッピングテーブル実装
- **ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: `EMOTION_TO_SENSORY_MAP` 辞書追加（6感情 × 5感覚）
- **仕様**: 例: sadness → visual(涙), auditory(静寂), tactile(冷たさ), olfactory(雨), gustatory(塩味)
- **テスト**: 6感情 × 5感覚すべてカバー

### ステップ 27: 文脈対応感覚詳細生成実装
- **ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: `generate_sensory_details(emotion_span, scene_context, pov)` 追加
- **仕様**: シーン文脈を含む LLM プロンプト、3-5文の具体的感覚描写出力
- **テスト**: 出力に ≥3 種の感覚モダリティ含有

### ステップ 28: フロー保持テキスト置換実装
- **ファイル**: `src/agents/enrichment/sensory.py`
- **変更内容**: `replace_with_sensory_expansion(text, emotion_spans, sensory_details)` 追加
- **仕様**: 抽象フレーズを拡張版で置換、段落フロー維持
- **テスト**: テキスト長 ~2.5倍、文破綻なし

### ステップ 29: 感覚モジュールを EnrichmentAgent に統合
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 感覚モジュールをインポートし `_expand_sensory_details()` で呼び出し
- **仕様**: 共有 LLM インスタンス使用、トークン予算遵守
- **テスト**: エンドツーエンドで感覚拡充済みテキスト生成

### ステップ 30: 感覚拡充メタデータ追加
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: `enrichment_metadata["sensory"] = [{"original_phrase", "expanded_text", "emotion", "senses_covered"}]`
- **テスト**: 各拡充のメタデータ完全

---

## カテゴリ F: マルチメディアシナリオ（ステップ 31-36）

### ステップ 31: シーンタイプ分類器作成
- **ファイル**: `src/agents/enrichment/scene_classifier.py` (新規)
- **変更内容**: `classify_scene_type(text, writing_context) → List[SceneSegment]`
- **仕様**: `SceneSegment = {type, start, end, characters, tension_level}`
- **タイプ**: climax, battle, emotional_peak, revelation, romance, daily_life, transition

### ステップ 32: マンガ台本テンプレート作成
- **ファイル**: `prompts/enrichment/templates/manga_script.j2`
- **変更内容**: Jinja2 テンプレート（マンガ形式）
- **仕様**: コマ割り、セリフ、効果音、カメラ指示

### ステップ 33: ラジオドラマテンプレート作成
- **ファイル**: `prompts/enrichment/templates/radio_drama.j2`
- **変更内容**: Jinja2 テンプレート（ラジオ形式）
- **仕様**: 効果音キューボイスディレクション、ナレーション、セリフ

### ステップ 34: アニメ絵コンテテンプレート作成
- **ファイル**: `prompts/enrichment/templates/anime_storyboard.j2`
- **変更内容**: Jinja2 テンプレート（アニメ形式）
- **仕様**: カット番号、秒数、カメラ、アクション、セリフ、背景

### ステップ 35: 実写ショットリストテンプレート作成
- **ファイル**: `prompts/enrichment/templates/live_action_shots.j2`
- **変更内容**: Jinja2 テンプレート（実写形式）
- **仕様**: シーンスラッグ、ショットタイプ、レンズ、移動、出演者、VFXメモ

### ステップ 36: マルチメディアジェネレーター実装
- **ファイル**: `src/agents/enrichment/multimedia.py` (新規)
- **変更内容**: `generate_scenarios(scene_segments, text, templates) → Dict[format, str]`
- **仕様**: トリガーシーンごとに4テンプレートすべてレンダリング
- **テスト**: サンプル クライマックスシーンで4形式すべて有効出力

---

## カテゴリ G: スキルラッパー（ステップ 37-42）

### ステップ 37: v1 EnrichmentSkill ラッパー作成
- **ファイル**: `src/agents/skills/v1/enrichment_skill.py`
- **変更内容**: `WritingSkill` パターンで新規作成
- **仕様**:
```python
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.enrichment_agent import EnrichmentAgent

class EnrichmentSkill(SkillAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = EnrichmentAgent(*args, **kwargs)
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return await self._agent.execute(ctx)
```

### ステップ 38: v2 EnrichmentSkill ラッパー作成
- **ファイル**: `src/agents/skills/v2/enrichment_skill.py`
- **変更内容**: v1 と同一だが v2 パスからインポート（将来の A/B 用）
- **テスト**: 両方インポートエラーなし

### ステップ 39: v1 スキルを検出登録
- **ファイル**: `src/agents/skills/v1/__init__.py`
- **変更内容**: `from .enrichment_skill import EnrichmentSkill` を `__all__` に追加
- **テスト**: `SkillAgent.discover_skills("src.agents.skills.v1")` に EnrichmentSkill 含有

### ステップ 40: v2 スキルを検出登録
- **ファイル**: `src/agents/skills/v2/__init__.py`
- **変更内容**: v2 でも同様
- **テスト**: v2 で検出動作

### ステップ 41: EnrichmentAgent をスキルパッケージエクスポートに追加
- **ファイル**: `src/agents/__init__.py`
- **変更内容**: `from .enrichment_agent import EnrichmentAgent` をエクスポートに追加
- **テスト**: `from src.agents import EnrichmentAgent` 動作

### ステップ 42: Writing パッケージにエイリアス追加（任意）
- **ファイル**: `src/agents/writing/__init__.py`
- **変更内容**: 利便性インポート追加
- **テスト**: インポート動作

---

## カテゴリ H: マニフェスト統合（ステップ 43-48）

### ステップ 43: manifest.yaml に EnrichmentSkill エントリ追加
- **ファイル**: `src/agents/skills/manifest.yaml`
- **変更内容**: WritingSkill と AuditSkill の間に新スキル挿入
- **仕様**:
```yaml
  - name: EnrichmentSkill
    class: src.agents.skills.v1.enrichment_skill.EnrichmentSkill
    depends_on: [WritingSkill]
    runs_after: [WritingSkill]
    runs_before: [AuditSkill]
    config:
      enabled: true
      trivia_enabled: true
      citation_enabled: true
      sensory_enabled: true
      multimedia_enabled: true
```

### ステップ 44: WritingSkill 依存関係更新
- **ファイル**: `src/agents/skills/manifest.yaml`
- **変更内容**: WritingSkill `runs_before: [EnrichmentSkill]` に変更（was AuditSkill）
- **テスト**: トポロジカルソートで正しい順序

### ステップ 45: AuditSkill 依存関係更新
- **ファイル**: `src/agents/skills/manifest.yaml`
- **変更内容**: AuditSkill `depends_on: [EnrichmentSkill]`, `runs_after: [EnrichmentSkill]` に変更
- **テスト**: 循環依存なし

### ステップ 46: IllustrationSkill 依存関係確認
- **ファイル**: `src/agents/skills/manifest.yaml`
- **変更内容**: IllustrationSkill `depends_on: [AuditSkill]` は変更なし（Audit 後維持）
- **テスト**: 完全順序: Planning→Bible→ContextBuilder→Writing→Enrichment→Audit→Illustration

### ステップ 47: マニフェスト検証テスト追加
- **ファイル**: `tests/unit/test_manifest_phase4.py` (新規)
- **変更内容**: マニフェスト読み込み、正しいソート、循環なしをテスト
- **テスト**: `pytest tests/unit/test_manifest_phase4.py -v`

### ステップ 48: Orchestrator 実行順序検証
- **ファイル**: `tests/integration/test_enrichment_pipeline_order.py` (新規)
- **変更内容**: Orchestrator が正しい実行順序構築するか統合テスト
- **テスト**: v1/v2 両スキルパッケージで実行

---

## カテゴリ I: Orchestrator 配線（ステップ 49-54）

### ステップ 49: Orchestrator 設定に EnrichmentAgent ノード追加
- **ファイル**: Orchestrator ノード設定箇所（`nodes = {` で検索）
- **変更内容**: `AgentName.ENRICHMENT: enrichment_agent.run` を nodes dict に追加
- **仕様**: `AgentName` enum に `ENRICHMENT = "enrichment"` 追加必要
- **テスト**: Orchestrator インスタンス化エラーなし

### ステップ 50: AgentName Enum に ENRICHMENT 追加
- **ファイル**: `src/agents/orchestrator.py`
- **変更内容**: `AgentName` enum に `ENRICHMENT = "enrichment"` 追加（WRITING 後）
- **テスト**: Enum アクセス可能、重複値なし

### ステップ 51: WritingAgent 次エージェント更新
- **ファイル**: `src/agents/writing/agent.py`
- **変更内容**: 成功時 `next_agent=AgentName.ENRICHMENT` に変更（was ILLUSTRATION）
- **テスト**: WritingAgent が ENRICHMENT を next 返却

### ステップ 52: EnrichmentAgent 次エージェント設定
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 成功時 `next_agent=AgentName.AUDIT` 返却
- **テスト**: EnrichmentAgent が AUDIT を next 返却

### ステップ 53: AuditAgent 入力処理更新
- **ファイル**: `src/agents/audit_agent.py`
- **変更内容**: execute() で `ctx.artifacts.get("enriched_text")` 優先、フォールバック `drafted_text`
- **仕様**:
```python
enriched_text = ctx.artifacts.get("enriched_text")
drafted_text = enriched_text or ctx.artifacts.get("drafted_text")
```
- **テスト**: エンリッチメント有/無両方で AuditAgent 動作

### ステップ 54: Orchestrator に機能フラグチェック追加
- **ファイル**: `src/agents/orchestrator.py` または設定ローダー
- **変更内容**: `ENRICHMENT_ENABLED=false` 時は EnrichmentAgent ノードスキップ（Writing→Audit 直結）
- **テスト**: フラグOFFでパイプラインスキップ、ONで包含

---

## カテゴリ J: EventBus 統合（ステップ 55-60）

### ステップ 55: エンリッチメントイベント定数追加
- **ファイル**: `src/agents/event_bus.py`
- **変更内容**: `ENRICHMENT_STARTED`, `ENRICHMENT_COMPLETED`, `ENRICHMENT_STEP_COMPLETED` 追加
- **テスト**: 定数アクセス可能

### ステップ 56: enrichment.started イベント発行
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: execute() で `enrichment.started` 発行（book_id, ep_num 含む）
- **テスト**: EventBus 購読者でイベント受信

### ステップ 57: enrichment.step_completed イベント発行
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 4サブタスク各完了時に `enrichment.step_completed` 発行（ステップ名、統計含む）
- **テスト**: エンリッチメント1回実行で4ステップイベント

### ステップ 58: enrichment.completed イベント発行
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: 成功時に `enrichment_metadata` サマリー付きで発行
- **テスト**: 最終イベントに4メタデータカテゴリすべて含有

### ステップ 59: ブラインドレビュー互換性追加
- **ファイル**: `src/agents/enrichment_agent.py`
- **変更内容**: execute() で `ctx.artifacts.get("blind_review_mode")` チェック
- **仕様**: true 時、他エージェント出力漏洩リスクのあるトリビア/引用をスキップ
- **テスト**: blind_review_mode=true でスキップステップがメタデータに反映

### ステップ 60: EventBus 統合テスト追加
- **ファイル**: `tests/integration/test_enrichment_events.py` (新規)
- **変更内容**: 6イベントタイプが正しい順序で発行されるか検証
- **テスト**: `pytest tests/integration/test_enrichment_events.py -v`

---

## カテゴリ K: テスト・検証（ステップ 61-66）

### ステップ 61: 単体テスト - トリビア挿入
- **ファイル**: `tests/unit/test_enrichment_trivia.py` (新規)
- **変更内容**: GraphRAG+LLM モック、挿入/メタデータ/トークン予算検証
- **テスト**: `pytest tests/unit/test_enrichment_trivia.py -v`

### ステップ 62: 単体テスト - 引用付与
- **ファイル**: `tests/unit/test_enrichment_citations.py` (新規)
- **変更内容**: Bible 索引モック、脚注挿入/文献リスト形式検証
- **テスト**: `pytest tests/unit/test_enrichment_citations.py -v`

### ステップ 63: 単体テスト - 感覚拡充
- **ファイル**: `tests/unit/test_enrichment_sensory.py` (新規)
- **変更内容**: 感情検出、感覚生成、置換テスト
- **テスト**: `pytest tests/unit/test_enrichment_sensory.py -v`

### ステップ 64: 単体テスト - マルチメディア生成
- **ファイル**: `tests/unit/test_enrichment_multimedia.py` (新規)
- **変更内容**: シーン分類、4テンプレートレンダリングテスト
- **テスト**: `pytest tests/unit/test_enrichment_multimedia.py -v`

### ステップ 65: 統合テスト - フルエンリッチメントパイプライン
- **ファイル**: `tests/integration/test_enrichment_e2e.py` (新規)
- **変更内容**: WritingAgent → EnrichmentAgent → AuditAgent を実コンポーネント風に実行
- **テスト**: エンリッチメント済みテキストが監査通過、メタデータ完全

### ステップ 66: リグレッションテスト - 既存パイプライン無影響
- **ファイル**: `tests/integration/test_regression_phase4.py` (新規)
- **変更内容**: 既存 full_pipeline テストを `ENRICHMENT_ENABLED=false` で実行
- **テスト**: フェーズ1-3 すべてのテスト通過継続

---

## カテゴリ L: 観測性・運用（ステップ 67-72）

### ステップ 67: Prometheus メトリクス追加
- **ファイル**: `src/backend/observability/metrics.py`
- **変更内容**: 以下カウンター/ヒストグラム追加：
  - `enrichment_duration_seconds`
  - `enrichment_trivia_insertions_total`
  - `enrichment_citations_added_total`
  - `enrichment_sensory_expansions_total`
  - `enrichment_multimedia_scenarios_total`
  - `enrichment_token_usage`
  - `enrichment_errors_total`
- **テスト**: `/metrics` で公開確認

### ステップ 68: 設定に機能フラグ追加
- **ファイル**: `src/backend/config.py` または `config/system_plugins.yaml`
- **変更内容**: `ENRICHMENT_ENABLED = os.getenv("ENRICHMENT_ENABLED", "false").lower() == "true"`
- **テスト**: 環境変数で切替、パイプライン動作確認

### ステップ 69: 管理APIエンドポイント追加
- **ファイル**: `src/backend/api/admin.py` (または類似)
- **変更内容**:
  - `GET /admin/enrichment/status` - 設定、機能フラグ、統計
  - `POST /admin/enrichment/test` - サンプルテキストでエンリッチメント実行
  - `GET /admin/enrichment/metrics` - Prometheus メトリクススナップショット
- **テスト**: `curl` で期待JSON返却

### ステップ 70: ヘルスチェック追加
- **ファイル**: `src/backend/health.py` (または類似)
- **変更内容**: EnrichmentAgent ヘルスチェック（LLM接続、GraphRAG、プロンプトテンプレート）
- **テスト**: `/health` にエンリッチメントステータス含有

### ステップ 71: ドキュメント更新
- **ファイル**: `docs/ENRICHMENT_AGENT.md` (新規)
- **変更内容**: アーキテクチャ、設定、API、例、トラブルシューティング
- **テスト**: ドキュメント正常レンダリング

### ステップ 72: 最終E2E検証・サインオフ
- **ファイル**: N/A（実行）
- **変更内容**: `ENRICHMENT_ENABLED=true` でサンプル書籍フルパイプライン実行
- **検証チェックリスト**:
  - [ ] WritingAgent → EnrichmentAgent → AuditAgent → IllustrationAgent 完走
  - [ ] `enriched_text` が `drafted_text` より長い（トリビア+感覚）
  - [ ] `enriched_text` に脚注存在
  - [ ] クライマックスシーンでマルチメディアシナリオ生成
  - [ ] AuditAgent がエンリッチメント済みテキストで合格
  - [ ] Prometheus メトリクス増加
  - [ ] 各段階でイベント発行
  - [ ] 機能フラグOFFで元パイプラインに復帰
  - [ ] フェーズ1-3 テストにリグレッションなし
- **サインオフ**: すべて通過 → フェーズ4完了

---

## 依存関係グラフまとめ

```
A1-A6 (基盤) 
    ↓
B7-B12 (コアエージェント) ← A1-A6 依存
    ↓
C13-C18 (トリビア) ← B7-B9, A1, A3 依存
    ↓
D19-D24 (引用) ← B7-B10, A1, A4 依存
    ↓
E25-E30 (感覚) ← B7-B11, A1, A5, 新規sensoryモジュール 依存
    ↓
F31-F36 (マルチメディア) ← B7-B12, A1, A6, 新規テンプレート 依存
    ↓
G37-G42 (ラッパー) ← B7, F36 依存
    ↓
H43-H48 (マニフェスト) ← G37-G40 依存
    ↓
I49-I54 (Orchestrator) ← H43-H46, B8 依存
    ↓
J55-J60 (イベント) ← I49-I52, B8 依存
    ↓
K61-K66 (テスト) ← すべて上位 依存
    ↓
L67-L72 (観測性) ← K65-K66 依存
```

**合計: 72 原子的・テスト可能・順序付きステップ**