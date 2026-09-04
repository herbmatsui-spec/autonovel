# フェーズ2 詳細実装計画書

> 対象: `docs/FUTURE_IMPROVEMENT_GUIDELINES.md` §201-204 の3項目
> - **#1** ブラインドピアレビュー方式のフィードバックループ導入
> - **#3** 専門的オーディターエージェントによるマルチレイヤー品質保証
> - **#7** 反射的スクリーニングによるRAG精度向上
>
> 方針: 低性能LLMでも実装可能なよう、LLM呼び出しは **全8オーディター中4つ＋反射スクリーニングの関連性/適合性評価の計5回までに抑制**。残り4オーディターはルールベース＋軽量LLMジャッジで実装。KeyBERT等の重いNLPモデルは一切使わず、`rank-bm25`(既存依存)＋自前のtf-idf風キーフレーズ抽出で代替する。
>
> 全工程を **36ステップ** に分割。各ステップは1PR=1コミット完結できる粒度。

---

## 凡例

- **[DATA]** データ層/スキーマ
- **[SVC]** サービス層(純粋ロジック)
- **[AGT]** エージェント層(SkillAgent継承)
- **[EVT]** EventBus拡張
- **[CFG]** 設定ファイル
- **[TST]** テスト
- **[OBS]** 観測/Prometheus
- **[API]** FastAPI エンドポイント
- 🟢 = LLM呼び出しゼロまたは極小(プロンプト200トークン以下・temperature=0)
- 🟡 = LLM呼び出し1回/数千トークン
- 🔴 = LLM呼び出しは本番で必須だが、テスト時はモックで代替可能にする

---

## ステップ一覧

| # | カテゴリ | タイトル | LLM負荷 |
|---|---------|---------|---------|
| 1 | [DATA] | `audit_specialist_results` テーブル新設 | 🟢 |
| 2 | [DATA] | `rag_reflection_history` テーブル新設 | 🟢 |
| 3 | [DATA] | Alembic マイグレーション生成・適用 | 🟢 |
| 4 | [SVC] | `src/services/blind_review.py` に `BlindReviewGate` を実装 | 🟢 |
| 5 | [SVC] | `BlindReviewGate.scrub_payload()` 実装(参照禁止エージェント出力のキー除去) | 🟢 |
| 6 | [SVC] | `src/services/audit_aggregator.py` スケルトン＋重み正規化 | 🟢 |
| 7 | [CFG] | `config/audit_weights.yaml` デフォルト/ジャンル別/フェーズ別 | 🟢 |
| 8 | [AGT] | `ConsistencyAuditor` 実装(`SkillAgent`継承・ルールベース) | 🟢 |
| 9 | [AGT] | `CreativityAuditor` 実装(語彙多様性・Type-Token Ratio) | 🟢 |
| 10 | [AGT] | `ReaderHookAuditor` 実装(冒頭/末尾ヒューリスティック) | 🟢 |
| 11 | [AGT] | `EmotionCurveAuditor` 実装(テンション変動の分散/傾き) | 🟢 |
| 12 | [AGT] | `StyleAuditor` 実装(文体DNA遵守度=TF-IDFコサイン) | 🟢 |
| 13 | [AGT] | `FactualAuditor` 実装(GraphRAGと固有名詞突合) | 🟡 |
| 14 | [AGT] | `StructureAuditor` 実装(プロットツリー照合) | 🟡 |
| 15 | [AGT] | `MultimodalAuditor` 実装(挿絵プロンプト整合) | 🟡 |
| 16 | [EVT] | `EventBus.publish_blind()` 拡張 | 🟢 |
| 17 | [EVT] | `audit.specialist.started` / `audit.specialist.completed` イベント型定義 | 🟢 |
| 18 | [SVC] | `AuditAggregator.run_all()` 並列実行(asyncio.gather) | 🟢 |
| 19 | [SVC] | `AuditAggregator.aggregate()` 重み付き集約 | 🟢 |
| 20 | [AGT] | `src/agents/skills/v2/audit_skill.py` の偽実装を本物の並列起動に置換 | 🟢 |
| 21 | [SVC] | `src/services/reflective_rag.py` 新設 | 🟢 |
| 22 | [SVC] | `_bm25_keyword_extract()` 実装(rank-bm25を流用) | 🟢 |
| 23 | [SVC] | `_context_fit_check()` 実装(GraphRAGのis_forbidden属性) | 🟢 |
| 24 | [SVC] | `ReflectiveRAGService.retrieve_with_reflection()` ループ本体 | 🟢 |
| 25 | [SVC] | `rag_service.retrieve_context()` から `reflective_rag` への委譲 | 🟢 |
| 26 | [TST] | 単体: `BlindReviewGate` 全13ケース | 🟢 |
| 27 | [TST] | 単体: 8オーディターのスコア算出スナップショット | 🟢 |
| 28 | [TST] | 単体: `AuditAggregator` 並列・重み集約 | 🟢 |
| 29 | [TST] | 単体: `ReflectiveRAGService` ループ収束/最大反復 | 🟢 |
| 30 | [TST] | 結合: 3案ガチャでブラインドピアレビュー適用 | 🟢 |
| 31 | [TST] | 結合: 監査失敗→次元別再生成ループ | 🟡 |
| 32 | [TST] | 結合: 反射スクリーニングT=0/1/3 でクエリ長と最終K件の変化 | 🟢 |
| 33 | [OBS] | Prometheus: `blind_review_blocked_keys_total`, `specialist_audit_duration_seconds`, `reflective_rag_iterations`, `rag_reflection_convergence_total` | 🟢 |
| 34 | [API] | `/admin/audit/specialists`, `/admin/audit/aggregate_test` | 🟢 |
| 35 | [API] | `/admin/rag/reflection_test`, `/admin/rag/reflection_stats` | 🟢 |
| 36 | [OBS] | E2E: `tests/e2e/phase2_full_flow.py` ＋ CHANGELOG/IMPLEMENTATION_SUMMARY更新 | 🟢 |

---

## 各ステップ詳細

### Step 1. [DATA] `audit_specialist_results` テーブル新設
- 場所: `src/models/audit.py` に `AuditSpecialistResult` を追加
- カラム: `id, book_id, chapter_number, specialist_name(Consistency/Creativity/...), score(0-100), feedback_json, suggestions_json, evaluated_at, evaluator_version("v2-phase2")`
- インデックス: `(book_id, chapter_number)`

### Step 2. [DATA] `rag_reflection_history` テーブル新設
- カラム: `id, session_id, book_id, original_query, refined_queries(json配列), iterations, final_doc_count, converged(bool), created_at`
- RAGの反射履歴を時系列保存(品質分析用)

### Step 3. [DATA] Alembic マイグレーション生成・適用
- `alembic revision --autogenerate -m "phase2_audit_specialist_rag_reflection"`
- マイグレーション適用後、`book_scores` テーブルへの外部キー制約も追加(任意)

### Step 4. [SVC] `BlindReviewGate` 骨格
- 場所: `src/services/blind_review.py`(新規)
- 責務: フィードバック配信時に「参照禁止エージェント」の出力をマスク
- 公開API:
  ```python
  class BlindReviewGate:
      def __init__(self, forbidden_agents: list[str], mode: Literal["scrub", "hash"] = "scrub"):
          ...
      def scrub_payload(self, payload: dict, target_agent: str) -> dict: ...
      def is_blocked(self, source_agent: str, target_agent: str) -> bool: ...
  ```
- `mode="hash"` は決定論的テスト用(同じ入力→同じハッシュ)

### Step 5. [SVC] `scrub_payload()` 実装
- 禁止エージェントのキー(例: `"planning_output"`, `"plot_tree"`, `"bible_snapshot"`)を **再帰的に** 削除または置換
- `replacement_token = f"<BLOCKED:{source_agent}>"`
- 深いネスト対応: `_deep_scrub(obj, blocked_keys)` をヘルパ化

### Step 6. [SVC] `AuditAggregator` 骨格
- 場所: `src/services/audit_aggregator.py`(新規)
- 責務: 8名の specialist を asyncio.gather で並列実行し、yaml 重み付きで集約
- コンストラクタ:
  ```python
  class AuditAggregator:
      def __init__(self, specialists: list[SpecialistAuditor], weights: dict[str, float]):
          self._validate_weights(weights)  # 合計=1.0を強制
          ...
  ```
- 空の `aggregate()` は Step 18 で実装

### Step 7. [CFG] `config/audit_weights.yaml`
```yaml
default:
  consistency: 0.20
  creativity: 0.15
  reader_hook: 0.15
  emotion_curve: 0.15
  style: 0.10
  factual: 0.10
  structure: 0.10
  multimodal: 0.05

by_genre:
  literary:        # 重みをdefaultへ合流させる(上書き不要)
  entertainment:   # entertainmentはreader_hook+0.05, structure-0.05
    reader_hook: 0.20
    structure: 0.05
  educational:     # factual+0.10, creativity-0.05, multimodal-0.05
    factual: 0.20
    creativity: 0.10
    multimodal: 0.00

by_phase:
  planning:        # 初期=創造性重視
    creativity: 0.25
    structure: 0.15
    reader_hook: 0.05
  mid_writing:     # 中盤=一貫性+事実性重視
    consistency: 0.25
    factual: 0.20
    creativity: 0.05
  climax:          # 終盤=カタルシス重視
    emotion_curve: 0.25
    reader_hook: 0.20
```
- ローダ: `src/config/audit_weights.py` で `load_weights(genre, phase)` 実装

### Step 8. [AGT] `ConsistencyAuditor`
- 継承: `SkillAgent`
- 入力: `ctx.artifacts["draft_text"]`, `ctx.artifacts["world_bible_snapshot"]`
- 出力: スコア 0-100 + feedback("矛盾候補: X章でAと言ったが本章でBと矛盾")
- **LLM呼び出しゼロ**: 固有名詞の出現頻度/共起を `world_bible_snapshot` と突き合わせるだけ
- ベースライン指標: 固有名詞マッチング率(0.0-1.0)×100

### Step 9. [AGT] `CreativityAuditor`
- **LLM呼び出しゼロ**
- 指標: Type-Token Ratio(TTR), 4-gram の繰り返し率, 形容詞/副詞の多様性
- スコア = `0.4*TTR_norm + 0.3*(1-repeat_4gram) + 0.3*adj_adv_diversity`
- 100点満点に正規化

### Step 10. [AGT] `ReaderHookAuditor`
- **LLM呼び出しゼロ**
- 冒頭評価: 先頭200文字から「疑問符・未完文・呼びかけ・時間/場所設定キーワード」の有無を加点
- 末尾評価: 最終200文字から「未解決代名詞・三点リーダ・感嘆符・問い」の有無を加点
- スコア = 冒頭40点 + 末尾60点

### Step 11. [AGT] `EmotionCurveAuditor`
- **LLM呼び出しゼロ**
- `prompts/emotional_hook_vocabulary.py`(既存)の語彙辞書を使用
- 文章を5文ごとに分割し、各セグメントの感情極性(辞書マッチ数/総単語数)を算出
- 指標: 分散(起伏の大きさ)、最大-最小(カタルシス強度)、最終→冒頭の符号反転
- 100点満点に正規化

### Step 12. [AGT] `StyleAuditor`
- **LLM呼び出しゼロ**
- 既存 `style_distiller.py` の文体DNA(profile)を入力とし、本文の BoW を `rank_bm25` のTF-IDFでベクトル化
- コサイン類似度を 0-100 にスケール
- 補助指標: 一人称/三人称比率、口語/文語比率

### Step 13. [AGT] `FactualAuditor` 🟡
- **LLM呼び出し 1回** (代替: ルールのみで初期実装し、Step 31 の結合テストで実LLMと突き合わせ)
- 入力: `draft_text`, `world_bible_snapshot`
- プロンプト: 「次の本文が、与えた世界観設定と矛盾する箇所を列挙せよ」(出力≤300トークン)
- スコア = `(1 - 矛盾件数/10)*100`
- フォールバック: LLM失敗時は Step 8 と同じ固有名詞マッチに縮退

### Step 14. [AGT] `StructureAuditor` 🟡
- **LLM呼び出し 1回**(同様フォールバック可)
- 入力: `draft_text`, `plot_tree`
- プロンプト: 「次の本文は、与えたプロットツリーのどのノードを消化したか。未消化ノードを列挙」(出力≤400トークン)
- スコア = `(消化ノード/全ノード)*100`

### Step 15. [AGT] `MultimodalAuditor` 🟡
- **LLM呼び出し 1回**
- 入力: `draft_text`, `illustration_prompts`(該当シーン分)
- プロンプト: 「本文の焦点(被写体・色調・感情)と、挿絵プロンプトの焦点が一致するか判定」(出力≤200トークン)
- スコア = `一致度*100`(0.0-1.0をLLMに返却させる)

### Step 16. [EVT] `EventBus.publish_blind()` 拡張
- 場所: `src/agents/event_bus.py`
- 追加API:
  ```python
  async def publish_blind(self, event: AgentEvent, gate: BlindReviewGate) -> List[asyncio.Task]:
      scrubbed = gate.scrub_payload(event.payload, event.agent)
      return await self.publish(AgentEvent(...scrubbed..., event.agent, event.correlation_id))
  ```
- 既存 `publish()` はそのまま温存(後方互換)

### Step 17. [EVT] specialist イベント型定義
- `AgentName` 列挙体に `AUDIT_CONSISTENCY`, `AUDIT_CREATIVITY`, ..., `AUDIT_MULTIMODAL` を追加(8種)
- イベント名定数:
  ```python
  AUDIT_SPECIALIST_STARTED = "audit.specialist.started"
  AUDIT_SPECIALIST_COMPLETED = "audit.specialist.completed"
  ```
- `audit.specialist.started` ペイロード: `{specialist, book_id, chapter_number, correlation_id}`
- `audit.specialist.completed` ペイロード: 完了結果(score, feedback, suggestions)

### Step 18. [SVC] `AuditAggregator.run_all()`
- `asyncio.gather(*[self._run_one(s, ctx) for s in self.specialists], return_exceptions=True)`
- 各 `_run_one` は:
  1. `audit.specialist.started` を `publish_async`
  2. `s.execute(ctx)` を `await`
  3. 結果を `self._results[book_id][chapter_number][specialist] = ...` に保存
  4. `audit.specialist.completed` を `publish_async`
  5. `AgentResult` 風タプルを返却

### Step 19. [SVC] `AuditAggregator.aggregate()`
- `book_id, chapter_number` をキーに各 specialist のスコアを引当
- `load_weights(genre, phase)` で重みを取得
- `overall = sum(score * weight)`, 各次元もそのまま返す
- 不在 specialist がある場合は重みを再正規化(合計=1.0を保つ)
- 戻り値: `BookScoreResult` dataclass(overall, by_specialist, missing)

### Step 20. [AGT] `audit_skill.py` v2 偽実装の置換
- 現状の `_v2_enhancements` フラグ＋log だけの実装を削除
- 新実装:
  ```python
  class AuditSkillAgent(SkillAgent):
      async def execute(self, ctx):
          aggregator = AuditAggregator.from_config(ctx)
          await aggregator.run_all(ctx)
          result = aggregator.aggregate(ctx.book_id, ctx.ep_num)
          ctx.artifacts["audit_v2_result"] = result.__dict__
          ctx.artifacts["regeneration_focus"] = result.lowest_dimension()
          return AgentResult(next_agent=AgentName.ILLUSTRATION, artifacts=ctx.artifacts)
  ```
- `regeneration_focus` は Phase 1 で既に wiring 済み(再生成ループが次元別にトリガされる)

### Step 21. [SVC] `ReflectiveRAGService` 骨格
- 場所: `src/services/reflective_rag.py`(新規)
- 責務: 初期検索→関連性評価→適合性チェック→フィルタ→クエリ精緻化→再検索のループ
- 公開API:
  ```python
  class ReflectiveRAGService:
      async def retrieve_with_reflection(
          self, session, *, query: str, book_id: int, top_k: int = 5,
          max_iter: int = 3, relevance_threshold: float = 0.5,
      ) -> ReflectiveRetrievalResult: ...
  ```

### Step 22. [SVC] `_bm25_keyword_extract()`
- `rank_bm25.BM25Okapi`(既存依存)で初期Top-K文書を再スコアリング
- 上位M件から「文書頻度の低いトークン上位N語」を抽出(簡易tf-idf的)
- **KeyBERT不使用**(依存追加を避ける)
- 出力: `list[str]`(キーワードN語)

### Step 23. [SVC] `_context_fit_check()`
- GraphRAGから `world_bible` の `is_forbidden / is_retired` 属性を取得
- 各取得文書のエンティティIDと照合し、禁則・廃止エンティティを含む文書は **大幅減点**
- スコア: `0.0(完全に矛盾) - 1.0(完全整合)`
- LLM呼び出しゼロ

### Step 24. [SVC] `retrieve_with_reflection()` ループ本体
- 擬似コード:
  ```python
  for i in range(max_iter):
      candidates = self._initial_search(session, query, top_k=10)
      scored = [
          (doc,
           0.6 * cosine_sim(doc, query) + 0.4 * context_fit_check(doc))
          for doc in candidates
      ]
      filtered = [d for d, s in scored if s >= relevance_threshold]
      if len(filtered) >= top_k:
          converged = True
          break
      keywords = self._bm25_keyword_extract(filtered or candidates, n=5)
      query = f"{query} {' '.join(keywords)}"  # AND条件化
  return ReflectiveRetrievalResult(filtered, iterations=i+1, history=...)
  ```
- 終了条件: `len(filtered) >= top_k` OR `i == max_iter-1`

### Step 25. [SVC] `rag_service.retrieve_context()` から委譲
- 既存 `GraphRAGService.retrieve_for_episode` は温存
- 新メソッド `GraphRAGService.retrieve_with_reflection()` を追加し、委譲
- 設定 `settings.RAG_REFLECTION_ENABLED`(bool)で **機能フラグ切替**(デフォルトON)

### Step 26. [TST] 単体: `BlindReviewGate`
- 場所: `tests/unit/test_blind_review.py`
- ケース:
  1. 禁止エージェント出力キーが除去される
  2. ネスト深い payload も再帰的に除去
  3. 許可エージェント出力キーは保持
  4. `mode="hash"` で同一入力→同一ハッシュ(決定論)
  5. `mode="hash"` で異なる入力→異なるハッシュ
  6. `is_blocked()` が source/target 組合せで正しく判定
  7. 空 payload でも例外なし
  8. blocked_keys 未指定時は何もしない
  9. blocked_keys に list 値が含まれる場合の部分保持
  10. blocked_keys に dict 値が含まれる場合の再帰
  11. JSON シリアライズ往復で壊れない
  12. 置換トークンがUnicode安全
  13. パフォーマンステスト(100KB payload < 50ms)

### Step 27. [TST] 単体: 8オーディター
- 場所: `tests/unit/test_specialist_auditors.py`
- 各オーディターについて:
  1. 既知の入力に対しスコアが想定レンジ(0-100)に収まる
  2. feedback が空でない
  3. suggestions が list[str]
  4. LLM呼び出しありの3種(Factual/Structure/Multimodal)はLLMをモック
  5. LLM例外時に縮退スコアを返す
  6. スコアが極端にバイアスしない(同じ入力→同じ出力)
  7. 重複入力で副作用なし

### Step 28. [TST] 単体: `AuditAggregator`
- 場所: `tests/unit/test_audit_aggregator.py`
- ケース:
  1. 8名すべて並列実行され、`asyncio.gather` の完了を待つ
  2. 重み合計が1.0でないと例外
  3. 1名失敗しても他は完走し `return_exceptions=True` が機能
  4. 失敗 specialist を `missing` リストに格納
  5. 重みは `genre`/`phase` で切替わる
  6. aggregate 結果が `BookScoreResult` 型
  7. `lowest_dimension()` が最低スコアの specialist 名を返す
  8. イベント `audit.specialist.started` / `audit.specialist.completed` が publish される

### Step 29. [TST] 単体: `ReflectiveRAGService`
- 場所: `tests/unit/test_reflective_rag.py`
- ケース:
  1. 1回目で十分(K件)→ 反復しない(`iterations == 1`)
  2. 2回目で収束→ `converged == True`
  3. max_iter 到達→ `converged == False`
  4. `relevance_threshold` を変えると結果件数が変わる
  5. context_fit 減点で禁則エンティティ文書が落ちる
  6. クエリが AND 条件で精緻化される(履歴に記録)
  7. 履歴が `rag_reflection_history` に保存される
  8. 初期検索0件→ 空結果で即返却

### Step 30. [TST] 結合: 3案ガチャ×ブラインドピアレビュー
- 場所: `tests/integration/test_planning_blind_review.py`
- シナリオ: PlanningAgent が3企画案出力 → 各案が独立した AuditAggregator インスタンスに渡される → BlindReviewGate が **自分の企画案の他案出力キー** をブロック → 3案とも他案を観測せず独立採点される
- 検証: 3案のスコアがそれぞれ異なるフィードバックを持つ(盲検なしだとほぼ同じフィードバックになる傾向)

### Step 31. [TST] 結合: 監査失敗→次元別再生成ループ
- 場所: `tests/integration/test_regeneration_by_dimension.py`
- LLMはモック
- シナリオ: AuditAggregator が `factual` を 50点で返却 → `regeneration_focus="factual"` → ContextBuilderAgent の `factual` 重視モードが起動 → 再生成 → 再スコア → 改善
- 検証: `regeneration_focus` が BookScoreCalculator の改善優先度ロジックに伝わる

### Step 32. [TST] 結合: 反射スクリーニング T=0/1/3
- 場所: `tests/integration/test_reflective_rag_loop.py`
- シナリオ: 同じクエリで `max_iter=0,1,3` を切替 → 結果の `final_doc_count` と `refined_queries` 長さが変化する
- 検証:
  1. T=0: 初期クエリと同じ、最終件数=初期Top-K
  2. T=1: 1回精緻化、最終件数≤初期Top-K
  3. T=3: 最大3回精緻化、`iterations ≤ 3`

### Step 33. [OBS] Prometheus メトリクス
- 場所: `src/backend/observability/metrics.py`(既存)に追記
- 追加:
  ```python
  blind_review_blocked_keys_total           # Counter (gate, source_agent)
  specialist_audit_duration_seconds         # Histogram (specialist, status)
  specialist_audit_score                    # Gauge   (specialist, book_id, chapter)
  reflective_rag_iterations                 # Histogram (book_id)
  reflective_rag_convergence_total          # Counter  (converged=true/false)
  reflective_rag_threshold_filtered_total   # Counter
  ```

### Step 34. [API] specialist 管理者API
- 場所: `src/backend/api/admin_audit.py`(新規)
- `GET /admin/audit/specialists` → 登録済み specialist 名とバージョン
- `POST /admin/audit/aggregate_test` → 任意の book_id/chapter で再集計(過去テキストをAuditAggregatorに流す)
- レスポンス: `overall, by_specialist, missing, weights_used`

### Step 35. [API] reflection 管理者API
- 場所: `src/backend/api/admin_rag.py`(新規)
- `POST /admin/rag/reflection_test` → 任意のクエリで反射スクリーニングを実行(`max_iter`, `top_k`, `relevance_threshold` 指定可)
- `GET /admin/rag/reflection_stats?book_id=X` → 反射履歴の統計(iterations平均、収束率、絞り込み率)

### Step 36. [OBS] E2E + ドキュメント更新
- 場所: `tests/e2e/phase2_full_flow.py`(新規)
- シナリオ:
  1. 企画→執筆→監査(8 specialist 並列)→盲検FB→再生成(必要時)→反射RAG
  2. すべて1プロセス内で完結
  3. 最終 BookScore が記録される
  4. Prometheusメトリクスが increment される
- ドキュメント:
  - `CHANGELOG.md`: 「Phase 2: Blind Peer Review / Multi-Layer Specialist Audit / Reflective RAG Screening」を追加
  - `IMPLEMENTATION_SUMMARY.md`: 「フェーズ2 完了」セクション追記
  - `docs/FUTURE_IMPROVEMENT_GUIDELINES.md` §201-204 のチェックボックスを更新(☐ → ☑)

---

## 低性能LLM向けの追加配慮

| 観点 | 対策 |
|------|------|
| LLM呼び出し総数 | 1監査サイクルあたり **最大5回** (Factual/Structure/Multimodal + 反射スクリーニングの適合性評価フォールバック1回)。反射スクリーニング自体はLLM不使用 |
| プロンプト長 | 各プロンプト ≤ 2000トークン入力 / ≤ 400トークン出力 |
| 失敗時の縮退 | LLM例外時は各オーディターが0LLM版ロジックに自動フォールバック。全体パイプラインは止まらない |
| 機能フラグ | `settings.BLIND_REVIEW_ENABLED`, `settings.MULTI_LAYER_AUDIT_ENABLED`, `settings.RAG_REFLECTION_ENABLED` で個別ON/OFF(段階的ロールアウト可能) |
| 決定論性 | `mode="hash"` の BlindReviewGate、`temperature=0` のLLM呼び出しでテスト再現性確保 |
| 既存機能との互換 | `SkillAgent` 継承・`AuditAggregator` 経由のため、既存 `AuditAgent` も `feature flag=OFF` で従来動作 |
| マイグレーション安全性 | ステップ1-3の新テーブルは nullable 許容、既存 BookScore と外部キーは **追加しない**(移行リスク低減) |

---

## 並行実行可能なステップグループ

依存関係上、以下のグループに分割して並列着手できます:

```
Group A (独立): Step 1-7   ← DATA + SVC骨格 + CFG
Group B (Aに依存): Step 8-15 ← 8 specialist 実装
Group C (Aに依存): Step 21-25 ← ReflectiveRAG実装
Group D (Aに依存): Step 4-5 と Step 16-17 ← BlindReview/EventBus
Group E (B,C,D完了後): Step 18-20 ← 統合
Group F (E完了後): Step 26-32 ← テスト
Group G (F完了後): Step 33-35 ← 観測/API
Group H (G完了後): Step 36   ← E2Eとドキュメント
```

実プロジェクトでは **3-4名のサブエージェントに A/B/C/D を並列割当** することで、工数を 1/3 程度に圧縮できます。

---

## 想定工数(低性能LLM = 1エージェント・逐次実装の場合)

- Step 1-7(データ+骨格): **0.5日**
- Step 8-15(8 specialist): **1.5日** (各0.2日×8)
- Step 16-17(EventBus): **0.2日**
- Step 18-20(統合): **0.3日**
- Step 21-25(ReflectiveRAG): **0.5日**
- Step 26-32(テスト7本): **1.0日**
- Step 33-35(観測/API): **0.3日**
- Step 36(E2E+ドキュメント): **0.2日**

**合計: 約 4.5日**(サブエージェント4並列なら約 1.5-2日)

---

## 完了条件(Definition of Done)

- [ ] 36ステップすべてPRマージ済み
- [ ] `pytest tests/unit/test_blind_review.py tests/unit/test_specialist_auditors.py tests/unit/test_audit_aggregator.py tests/unit/test_reflective_rag.py` が全てpass
- [ ] `pytest tests/integration/test_planning_blind_review.py tests/integration/test_regeneration_by_dimension.py tests/integration/test_reflective_rag_loop.py` が全てpass
- [ ] `pytest tests/e2e/phase2_full_flow.py` がpass
- [ ] Prometheusメトリクス4種が `curl /metrics` で確認できる
- [ ] `/admin/audit/aggregate_test` で `overall_score` が 0-100 で返る
- [ ] `/admin/rag/reflection_test` で `iterations` が 0-3 で返る
- [ ] CHANGELOG/IMPLEMENTATION_SUMMARY/FUTURE_IMPROVEMENT_GUIDELINES が更新済み
- [ ] 機能フラグ3種をOFFにすると既存挙動と一致(回帰なし)