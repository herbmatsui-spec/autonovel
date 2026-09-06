# 改善案 1-3 詳細実装計画書
## 24ステップ分割版（低性能LLM対応・段階的デリバリー）

---

## 改善案1: 強化ルールベースフォールバック精度統一
**目標**: 全8専門家の `_fallback` を「エンティティ関係グラフ + 意味的整合性チェック」基盤に統一し、LLMなしでも実用スコアを出せるようにする

### Step 1: 共通ユーティリティ作成 `src/agents/specialists/fallback_utils.py`
```python
# 最小APIのみ実装
- extract_entities(text: str, bible: dict) -> dict[str, set[str]]  # カテゴリ別エンティティ抽出
- build_relation_graph(bible: dict) -> dict[str, set[str]]        # エンティティ間関係（敵対/同盟/所有/所在）
- check_semantic_consistency(draft: str, graph: dict) -> float    # 0-1整合性スコア
- compute_coverage(draft: str, entities: set[str]) -> float       # 言及率
```
**受入**: 単体テスト `tests/unit/test_fallback_utils.py` で各関数が期待値返す

### Step 2: ConsistencyAuditor._fallback 書き換え
```python
# 置換ロジック
1. bibleから characters/locations/items/factions を抽出
2. relation_graph = build_relation_graph(bible)
3. consistency_score = check_semantic_consistency(draft, relation_graph)
4. coverage = compute_coverage(draft, all_entities)
5. score = 0.6 * consistency_score * 100 + 0.4 * coverage * 100
6. 矛盾詳細（死亡キャラ登場、場所瞬間移動等）を suggestions に列挙
```
**受入**: 既存テスト `test_consistency_auditor.py::test_contradiction_penalty` がスコア<50でパス

### Step 3: FactualAuditor._fallback 書き換え
```python
# 追加ロジック
1. 時代設定キーワード（中世/近未来/現代）を bible["meta"]["era"] から取得
2. era_inappropriate_terms = load_era_blacklist(era)  # YAML外部化
3. anachronism_penalty = len(found_anachronisms) * 15
4. entity_coverage = compute_coverage(draft, factual_entities)
5. score = max(20, entity_coverage * 80 - anachronism_penalty)
```
**受入**: 新テスト `test_factual_anachronism_detection` で現代語混入時にスコア大幅減

### Step 4: StructureAuditor._fallback 書き換え
```python
# キーワードカバレッジ → シーン構造解析へ
1. plot_tree を "intro,conflict,climax,resolution" 4フェーズに分割（区切り: "→" "、" "。"）
2. draft を同長セグメント4分割
3. 各フェーズごとのキーワードカバレッジ計測
4. ペース配分スコア = 各フェーズ文字数の分散逆数
5. score = 0.7 * avg_phase_coverage * 100 + 0.3 * pacing_score * 100
```
**受入**: `test_structure_pacing` 新設で冗長/駆け足ケース検知

### Step 5: ReaderHookAuditor._fallback 強化
```python
# キーワードヒット → 文構造・修辞解析へ
1. 冒頭200字: 疑問文/感嘆文/倒置法/省略 の頻度
2. 末尾200字: 未完了節/疑問/示唆/音・視覚描写 の頻度
3. 重み付けスコアリング（手書きルール、学習不要）
```
**受入**: 既存 `test_weak_hooks` がスコア10→30-40に改善

### Step 6: MultimodalAuditor._fallback 強化
```python
# bigram Jaccard → キャラ/小道具/感情トーンの三層マッチ
1. draft から (character, prop, emotion) トリプル抽出（正規表現ベース）
2. illustration_prompts から同トリプル抽出
3. 三層それぞれでJaccard計算 → 加重平均（キャラ0.5, 小道具0.3, 感情0.2）
```
**受入**: 新テスト `test_multimodal_triple_match` で焦点ズレ検知

### Step 7: StyleAuditor._fallback 微調整（既存で概ね良好）
```python
- BM25類似度を style_dna.sample_text と比較し 0.3 重みで加算
- 語尾一貫性スコアの閾値を 0.7→0.8 に引き上げ
```
**受入**: 既存テスト全パス、スコア分布が人手評価と相関上昇

### Step 8: EmotionCurveAuditor._fallback 微調整
```python
- セグメント分割を「段落」優先→「文末感情語密度変化点」に改善
- カタルシス語を CATHARSIS_WORDS + 直前の否定語チェックで誤検知除去
```
**受入**: `test_flat_text` スコア 20→35-40 に改善

### Step 9: 共通テストスイート拡充 `tests/unit/test_fallback_unified.py`
```python
# 全8専門家共通シナリオ
@pytest.mark.parametrize("auditor_class", [ConsistencyAuditor, ...])
async def test_fallback_no_llm_returns_reasonable_score(auditor_class):
    ctx = {"draft_text": SAMPLE_DRAFT, "world_bible_snapshot": SAMPLE_BIBLE, ...}
    auditor = auditor_class(llm=None)
    result = await auditor._safe_audit(ctx)
    assert result.degraded is True
    assert 30 <= result.score <= 90  # 極端値排除
    assert result.suggestions  # 具体的改善提案がある
```

---

## 改善案2: LLMジャッジ信頼度・校正機構
**目標**: `_judge_with_llm` が `confidence` 返却、分散大なら自動フォールバック

### Step 10: SpecialistAuditResult 拡張 `src/agents/specialist_auditor_base.py`
```python
@dataclass
class SpecialistAuditResult:
    ...
    confidence: float = 1.0           # 0-1, LLM自己評価信頼度
    reasoning_trace: str = ""         # 推論過程（デバッグ用）
    llm_raw_response: str = ""        # 生出力（監査用）
```
**受入**: 既存全テストパス（デフォルト値で互換性維持）

### Step 11: _judge_with_llm 戻り値変更
```python
# 返却: tuple[float, str, list[str], float, str, str]
#        score, critique, suggestions, confidence, reasoning, raw
```
**受入**: 全専門家の `audit()` 呼び出し箇所を一括置換（`sed` 可）

### Step 12: プロンプトに構造化出力指示追加
```python
# 各専門家の SYSTEM_PROMPT 末尾に追加
JSON_OUTPUT_INSTRUCTION = """
必ず以下のJSONのみ出力:
{
  "score": 0-100,
  "critique": "...",
  "suggestions": ["..."],
  "confidence": 0.0-1.0,
  "reasoning": "判定根拠の要約（100字以内）"
}
"""
```
**受入**: ダミーLLMテストで全フィールド取得確認

### Step 13: 信頼度閾値チェック・自動フォールバック
```python
# _safe_audit 内で
async def _safe_audit(self, ctx):
    try:
        result = await self.audit(ctx)
        if result.confidence < 0.6:  # 閾値は定数化
            logger.warning(f"{self.specialist_name}: low confidence {result.confidence}, falling back")
            fb = self._fallback(ctx)
            fb.error = f"low_confidence: {result.confidence}"
            return fb
        return result
    except LLMUnavailableError:
        ...
```
**受入**: `test_low_confidence_triggers_fallback` 新設（モックLLMで confidence=0.3 返却）

### Step 14: 複数回サンプリング・分散チェック（オプション・低コスト）
```python
# 環境変数 AUDIT_LLM_SAMPLES=3 で有効化
async def _judge_with_llm(self, prompt, system_prompt, samples=1):
    if samples <= 1: return await self._single_judge(...)
    scores = []
    for _ in range(samples):
        s, c, sug, conf, reas, raw = await self._single_judge(...)
        scores.append(s)
    if stdev(scores) > 15:  # 分散大
        raise LLMUnavailableError(f"High variance: {scores}")
    return mean(scores), ...
```
**受入**: 統合テストで分散大ケースがフォールバックに流れること確認

### Step 15: プロンプトバイアス補正係数（軽量版）
```python
# config/llm_bias_correction.yaml
bias_correction:
  consistency: 1.02   # 傾向: 甘め → *1.02
  creativity: 0.98    # 傾向: 厳しめ → *0.98
  ...
# 適用: score = min(100, score * correction_factor)
```
**受入**: 過去ログ分析スクリプトで係数算出→手動適用→分布中央値が50±5に収束

---

## 改善案3: ジャンル別重みA/Bテストフレームワーク
**目標**: 実トラフィックで重みバリアントを比較評価、データ駆動チューニング

### Step 16: 重みバリアントレジストリ `src/config/weight_variants.py`
```python
# YAMLではなくPython dictで管理（動的生成・バリデーション容易）
WEIGHT_VARIANTS = {
    "default_v1": {...},           # 現行
    "literary_v1": {...},
    "entertainment_v1": {...},
    # 実験用
    "literary_v2_consistency_up": {"consistency": 0.25, ...},
    "entertainment_v2_hook_up": {"reader_hook": 0.30, ...},
}
def get_variant(name: str) -> dict: ...
def register_variant(name: str, weights: dict): ...  # バリデーション付き
```

### Step 17: 実験割当ロジック `src/services/experiment_allocator.py`
```python
class ExperimentAllocator:
    def __init__(self, traffic_fraction: float = 0.01):  # 1%から開始
        self.traffic_fraction = traffic_fraction
    def allocate(self, book_id: int, genre: str) -> str:
        # 決定的ハッシュ割当（同一book_idは常に同一バリアント）
        hash_val = hashlib.md5(f"{book_id}:{genre}".encode()).hexdigest()
        bucket = int(hash_val, 16) % 10000
        if bucket < self.traffic_fraction * 10000:
            return self._select_variant(genre)  # ジャンルごとに候補からランダム
        return "default_v1"
```

### Step 18: AuditAggregatorNode に実験統合
```python
# adapter.py get_aggregator 内で
def get_aggregator(self, genre: str, phase: str, book_id: int) -> AuditAggregator:
    variant_name = self.experiment_allocator.allocate(book_id, genre)
    weights = weight_variants.get_variant(variant_name)
    # 既存ロジック継続...
    # 戻り値の BookScoreResult に variant_name 付与
```

### Step 19: メトリクス収集イベント発行
```python
# audit_aggregator.py _publish_completed 拡張
payload = {
    ...
    "weight_variant": variant_name,
    "genre": genre,
    "phase": phase,
    "overall_score": result.overall,
    "specialist_scores": result.by_specialist,
    "regeneration_triggered": score_result.overall < min_pass_score,
}
await event_bus.publish_async(AgentEvent(agent="audit.metrics", payload=payload, ...))
```

### Step 20: 集計ダッシュボード用クエリ・ビュー作成（SQL）
```sql
-- audit_metrics_mv (materialized view, 5分毎リフレッシュ)
CREATE MATERIALIZED VIEW audit_metrics_mv AS
SELECT
  weight_variant,
  genre,
  phase,
  COUNT(*) as samples,
  AVG(overall_score) as mean_score,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY overall_score) as median_score,
  STDDEV(overall_score) as std_score,
  SUM(CASE WHEN regeneration_triggered THEN 1 ELSE 0 END)::float / COUNT(*) as regen_rate
FROM audit_events
WHERE event_type = 'audit.aggregated'
GROUP BY weight_variant, genre, phase;
```

### Step 21: 自動統計的有意差判定スクリプト `scripts/analyze_ab_test.py`
```python
# 週次バッチで実行
def analyze():
    df = pd.read_sql("SELECT * FROM audit_metrics_mv", engine)
    for genre in df.genre.unique():
        for phase in df.phase.unique():
            sub = df[(df.genre==genre) & (df.phase==phase)]
            control = sub[sub.weight_variant==f"{genre}_v1"]
            treatments = sub[sub.weight_variant!=f"{genre}_v1"]
            for _, t in treatments.iterrows():
                # Welch's t-test + Cliff's delta (非パラメトリック)
                p_val = ttest_ind(control.scores, t.scores, equal_var=False).pvalue
                effect = cliffs_delta(control.scores, t.scores)
                if p_val < 0.05 and abs(effect) > 0.2:
                    alert(f"Variant {t.weight_variant} significant: p={p_val:.4f}, d={effect:.3f}")
```

### Step 22: 重み自動昇格ワークフロー（手動承認付き）
```python
# 解析結果 → Slack/メール通知 → 承認ボタン → weight_variants.py 更新 → デプロイ
# MVP: 通知のみ、手動マージで運用開始
```

### Step 23: 監視・アラート設定
```yaml
# .github/workflows/ab_test_monitor.yml
- name: Check fallback rate
  run: |
    python -c "
    import psycopg2, os
    cur.execute('SELECT AVG(CASE WHEN degraded THEN 1 ELSE 0 END) FROM specialist_results WHERE evaluated_at > NOW() - INTERVAL \"1 hour\"')
    rate = cur.fetchone()[0]
    if rate > 0.2: exit(1)
    "
```

### Step 24: ドキュメント・運用手順書
```markdown
# docs/AB_TEST_OPERATIONS.md
- 新バリアント追加手順
- トラフィック割合調整手順
- 有意差判定基準・昇格基準
- ロールバック手順
- 過去実験履歴・学び
```

---

## 実装順序・依存関係ガントチャート

```
Week 1 (Step 1-9):  フォールバック統一基盤
  Day 1-2: Step 1-2 (Consistency優先)
  Day 3-4: Step 3-4 (Factual, Structure)
  Day 5:   Step 5-8 (ReaderHook, Multimodal, Style, EmotionCurve)
  Day 6:   Step 9 (統合テスト・リグレッション確認)

Week 2 (Step 10-15): LLM信頼度機構
  Day 1-2: Step 10-12 (データ構造・プロンプト)
  Day 3:   Step 13 (自動フォールバック)
  Day 4:   Step 14 (サンプリング・分散チェック・任意)
  Day 5:   Step 15 (バイアス補正・係数算出スクリプト)

Week 3 (Step 16-24): A/B基盤
  Day 1-2: Step 16-18 (レジストリ・割当・統合)
  Day 3:   Step 19-20 (メトリクス・DBビュー)
  Day 4:   Step 21-22 (分析スクリプト・昇格フロー)
  Day 5:   Step 23-24 (監視・ドキュメント)
```

---

## 低性能LLM対応の工夫

| 箇所 | 対策 |
|------|------|
| フォールバック | 正規表現・辞書ルールのみ。学習・推論不要 |
| 信頼度 | LLMに「自信度0-1」を出力させるだけ（追加トークン約20） |
| バイアス補正 | 事後補正係数（乗算のみ）。オンライン学習不要 |
| A/B割当 | MD5ハッシュのみ。外部サービス不要 |
| 分析 | 週次バッチでSQL+Python。リアルタイム処理不要 |

---

## 完了定義（Definition of Done）

- [ ] 全Stepの単体テスト追加・パス
- [ ] 統合テスト `test_specialist_auditors_llm.py` 全パス
- [ ] フォールバックのみで運用した場合のスコア分布が人手評価と相関 ≥0.7
- [ ] A/B基盤をステージング環境で1週間稼働、エラー率<0.1%
- [ ] ドキュメント・運用手順書がチームレビュー済み