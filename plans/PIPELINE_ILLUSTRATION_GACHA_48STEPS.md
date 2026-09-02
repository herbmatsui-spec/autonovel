# 統合パイプライン / 挿絵 / Gacha+Digest 改善実装計画

対象 Issue: #5 (Pipeline Steps 40%)、#6 (Illustration 46%)、#7 (Gacha+Digest 44%)
方針: 各変更を「差分最小・テスト先行・既存 DI / Huey / Redis を再利用」の原則で 1 ステップ ≒ 1 commit 単位に分解する。低性能 LLM でも各ステップ単独で実装可能な粒度にしている。

凡例:
- 🔧 実装 / ✏️ テスト追加 / 🔍 調査 / 📚 ドキュメント
- 工数目安: S=数時間 / M=1日 / L=2-3日

---

## フェーズ A: 共通基盤 (Day 1-2) — 先に全 Phase が使う土台を作る

### Step 1 🔧 S  `WorkflowContext.warnings: list[str]` フィールド追加
- 場所: `src/services/pipeline_base.py:17`
- 変更: `warnings: list[str] = Field(default_factory=list)` を追加
- 検証: 既存テストが通る (`WorkflowContext(genre="x", ...)` での生成が壊れない)
- コミット: `feat(pipeline): add ctx.warnings list for non-fatal step messages`

### Step 2 🔧 S  `_emit_skip(reporter, ctx, step, reason)` ヘルパー
- 場所: 新規 `src/services/pipeline_steps.py` の上部に追加
- 役割: `reporter.report(..., "warning")` + `ctx.warnings.append(...)` + `metrics.increment(f"step_skip.{step}")` を一発で呼ぶ
- 検証: import 可能、型ヒント正しい
- コミット: `feat(pipeline): add _emit_skip helper for non-fatal skips`

### Step 3 🔧 S  `metrics` シングルトン import 確立
- 場所: `src/services/pipeline_steps.py:29` 直下に `from src.backend.observability.health import metrics`
- 検証: `from src.services.pipeline_steps import metrics` で import 可能
- コミット: `chore(pipeline): import metrics for skip observability`

### Step 4 🔧 S  `illustration_settings` デフォルト値の安全化
- 場所: `pipeline_base.py:45`
- 変更: 既に `default_factory=dict` だが、`enable_illustration=False` 時に `illustration_settings` が `{}` でも OK か docstring に明記
- コミット: `docs(pipeline): document illustration_settings defaults`

---

## フェーズ B: IllustrationStep 改修 (Day 2-3) — Issue #5/#6 共通

### Step 5 🔧 S  `pipeline_steps.py` から `os.getenv` 削除
- 場所: `pipeline_steps.py:423, 427`
- 変更: `import os` を削除し、`api_key` を `ctx.illustration_settings.get("api_key", "")` から取得 (フォールバック空文字)
- リスク: 空文字で `ImageService` 初期化 → Step 6 で修正
- コミット: `refactor(pipeline): remove os.getenv in IllustrationStep`

### Step 6 🔧 M  `ImageService.__init__` で api_key 必須化
- 場所: `src/services/image_service.py:21-29`
- 変更: `api_key: str` を必須に、空文字なら `ValueError("GOOGLE_GENAI_API_KEY is required")` を送出
- 既存呼び出し側を grep (`rg "ImageService(" src tests`)、該当箇所を事前確認
- 検証: `tests/test_illustration_agent.py` のフィクスチャで api_key 渡す
- コミット: `feat(image): make ImageService api_key mandatory`

### Step 7 🔧 S  `IllustrationStep` で `ctx.engine` 経由でサービス取得
- 場所: `pipeline_steps.py:404-444`
- 変更:
  ```python
  ill_workflow = IllustrationWorkflow(
      illustration_agent=engine.illustration_agent,
      repo=engine.repo,
  )
  ```
  ※ `engine.illustration_agent` 追加が前提 → Step 8
- コミット: `refactor(pipeline): IllustrationStep uses engine DI`

### Step 8 🔧 S  `UltimateHegemonyEngine` に `illustration_agent` プロパティ追加
- 場所: `src/backend/engine.py` (`UltimateHegemonyEngine.__init__` 周辺)
- 変更: `self.illustration_agent = IllustrationAgent(image_service=ImageService(api_key=self.api_key), repo=self.repo, llm=self.llm)`
- コミット: `feat(engine): expose illustration_agent property`

### Step 9 ✏️ S  `test_illustration_settings_required` 追加
- `tests/test_image_service.py` 新規
- `ImageService(api_key="")` が `ValueError` を送出することを確認
- コミット: `test(image): assert api_key required`

### Step 10 ✏️ S  IllustrationStep の「enable=False 早期 return」テスト
- 場所: `tests/test_unified_pipeline.py` (既存ファイルへ追加)
- 検証: `ctx.enable_illustration=False` で `IllustrationStep().execute(...)` が `True` 返却し、`engine.illustration_agent` が呼ばれない (モックで検知)
- コミット: `test(pipeline): IllustrationStep short-circuits when disabled`

### Step 11 ✏️ S  IllustrationStep の `book_id=None` skip を `ctx.warnings` で検知可能に
- 場所: `pipeline_steps.py:414` → `_emit_skip(reporter, ctx, "illustration", "book_id is None")` を呼ぶ
- 検証テスト: skip 実行後 `ctx.warnings == ["illustration: book_id is None"]`
- コミット: `feat(pipeline): IllustrationStep skip is observable`

### Step 12 ✏️ M  `test_unified_pipeline.py` に実 IllustrationStep ロジックテスト追加
- 既存テストは全 Step を AsyncMock 置換している → 本 Step では IllustrationStep だけ実物を使い、`engine.illustration_agent.run` のみモック
- コミット: `test(pipeline): exercise real IllustrationStep logic`

---

## フェーズ C: MarketingStep 改修 (Day 3-4)

### Step 13 🔧 S  MarketingStep のフォールバック 3 段化 (プリセット→LLM→テンプレ)
- 場所: `pipeline_steps.py:451-499`
- 構造:
  ```python
  if title_templates:                  # 1段: プリセット
      ctx.title = title_templates[0]
  elif ctx.title is empty:              # 2段: LLM
      prompt = "次のコンセプトから魅力的な日本語タイトルを3案: " + ctx.concept
      res = await engine.llm.generate(prompt, {})
      ctx.title = res.split("\n")[0]
  else:                                 # 3段: 固定テンプレ
      ctx.title = f"{ctx.genre}の物語"
  ```
- コミット: `feat(pipeline): MarketingStep 3-tier title fallback`

### Step 14 🔧 S  `ctx.archetype_key` 未設定時に Easy モード空データ化しない
- 場所: `pipeline_steps.py:466`
- 変更: `preset = load_preset_for_pipeline(ctx.genre, ctx.archetype_key or "default")` (空文字ガード)
- 追加: `if not preset: preset = {"marketing": {}, "titles": {}}` で KeyError 防止
- コミット: `fix(pipeline): MarketingStep handles missing archetype_key`

### Step 15 ✏️ S  `test_marketing_step_preset_path` 追加
- プリセットに `title_templates=["王道の剣"]` を与えた時、ctx.title がそれになる
- コミット: `test(pipeline): MarketingStep preset path`

### Step 16 ✏️ S  `test_marketing_step_llm_fallback` 追加
- プリセット空 + `engine.llm.generate` が AsyncMock 戻り値 → タイトル設定
- コミット: `test(pipeline): MarketingStep LLM fallback path`

### Step 17 ✏️ S  `test_marketing_step_template_fallback` 追加
- プリセット空 + LLM 例外 → `{genre}の物語`
- コミット: `test(pipeline): MarketingStep template fallback path`

### Step 18 ✏️ S  `test_marketing_step_disabled` 追加
- `ctx.enable_marketing=False` で早期 return、ctx.marketing_pack は作られない
- コミット: `test(pipeline): MarketingStep disabled short-circuit`

---

## フェーズ D: CatharsisAnalysisStep 改修 (Day 4-5)

### Step 19 🔧 S  `book_id is None` skip を `ctx.warnings` に積む
- 場所: `pipeline_steps.py:200-201`
- 変更: 早期 return 直前に `_emit_skip(reporter, ctx, "catharsis", "book_id is None; skipping analysis")`
- コミット: `fix(pipeline): CatharsisAnalysis skip is observable`

### Step 20 🔧 S  `enable_catharsis_analysis=False` skip も `_emit_skip` に統一
- `pipeline_steps.py:198-199` を同様に
- コミット: `refactor(pipeline): unify catharsis skip reason`

### Step 21 ✏️ S  `test_catharsis_step_skip_observable` 追加
- `ctx.enable_catharsis_analysis=True, ctx.book_id=None` → `ctx.warnings` に "catharsis" 含む
- コミット: `test(pipeline): catharsis skip surfaced to ctx.warnings`

### Step 22 ✏️ M  `test_catharsis_step_real_analysis` 追加
- 実 Step + `engine.repo.plot.get_all_plots` を AsyncMock で 3 プロット返却 → `ctx.catharsis_pattern` 設定確認
- コミット: `test(pipeline): catharsis real logic covered`

---

## フェーズ E: PackageStep 安全性 (Day 5)

### Step 23 🔧 S  PackageStep の `enable_marketing` アクセス防御
- 場所: `pipeline_steps.py:373-397` + `MarketingStep` 実行順の保証
- 変更: `ctx.marketing_pack` が無い場合に `getattr(ctx, "marketing_pack", {})` で参照
- コミット: `fix(pipeline): PackageStep tolerant of marketing disabled`

### Step 24 ✏️ S  `test_package_step_with_marketing_disabled` 追加
- `ctx.enable_marketing=False` で全 Step 走らせ、`AttributeError` が出ない
- コミット: `test(pipeline): PackageStep runs without marketing`

---

## フェーズ F: 挿絵ルータ DI 化 (Day 5-7) — Issue #6

### Step 25 🔍 S  既存ルータの import 構造を確認
- 場所: `src/backend/routers/illustrations.py:1-20`
- 確認: `AppContainer` が import されていないバグを grep
- コミット: なし (調査のみ)

### Step 26 🔧 M  `src/dependencies.py` 新規ファイル作成
- 内容:
  ```python
  from fastapi import Depends
  from src.core.container import AppContainer
  from src.services.image_service import ImageService
  from src.agents.illustration_agent import IllustrationAgent

  def get_illustration_workflow():
      container = AppContainer()
      container.api_key.override(os.environ["GOOGLE_GENAI_API_KEY"])  # or config
      return container.illustration_workflow()
  ```
- コミット: `feat(deps): introduce src.dependencies for illustration DI`

### Step 27 🔧 S  `routers/illustrations.py:17` のバグ修正
- 変更: `get_illustration_workflow` を `from src.dependencies import get_illustration_workflow` で import
- コミット: `fix(router): illustration DI import`

### Step 28 ✏️ S  `tests/test_illustration_router.py` 新規 — DI 解決テスト
- `TestClient(app)` で `/api/illustrations/health` (or 既存 GET) を叩いて 500 にならない
- コミット: `test(router): illustration router boots without AppContainer errors`

### Step 29 🔧 M  `/api/illustrations/batch` を Huey タスク化
- 新規タスク: `src/backend/tasks/illustration_tasks.py` に `illustrate_batch_task`
- ルータは `{task_id, status: "queued"}` 即返却
- コミット: `feat(tasks): huey illustration batch task`

### Step 30 🔧 S  `GET /api/illustrations/status/{task_id}` 追加
- `BookRepository.get_task_status` があれば再利用、無ければ `Task` モデルへ status 書き戻し
- コミット: `feat(router): illustration task status endpoint`

### Step 31 ✏️ M  `test_illustration_batch_e2e` (モック Huey) 追加
- `immediate=True` モードで Huey を起動 → バッチ → status 取得 → completed
- コミット: `test(illustration): e2e batch flow`

### Step 32 ✏️ S  `test_image_service_r15_safety` 追加
- `SafetyLevel.R15_CONTENT` → `_build_safety_settings` が `BLOCK_MOST` を返す
- コミット: `test(image): R15 safety threshold`

### Step 33 ✏️ S  `test_illustration_agent_episode_r15_prompt` 既存テスト強化
- 既存テストは prompt 文字列に "R15" を含むかのみ確認 → `safety_settings` まで検証追加
- コミット: `test(illustration): R15 safety propagates to API call`

### Step 34 ✏️ M  E2E: `test_illustration_full_flow_e2e`
- `app` 起動 → `POST /api/illustrations/generate` → `image_url` 取得 (Imagen は完全モック)
- コミット: `test(e2e): full illustration generation flow`

---

## フェーズ G: Gacha / Digest 永続化 (Day 8-10) — Issue #7

### Step 35 🔍 S  Redis 接続の確認
- `src/services/redis_cache.py:740` の `get_redis_cache` を確認、既存 EasyMode ルータから呼べるか
- コミット: なし

### Step 36 🔧 M  `GachaService` を `db=DatabaseManager` 必須化
- 場所: `src/services/gacha_service.py:31-37`
- 変更:
  ```python
  def __init__(self, llm_service, db: Any):
      if db is None:
          raise ValueError("db=DatabaseManager is required (in-memory cache is removed)")
      ...
  ```
  + `_GACHA_CACHE` 削除
- 既存呼び出し側 (routers/easy_mode.py:311) は既に `db=db` を渡している → 影響なし
- コミット: `feat(gacha): require db, remove in-memory cache`

### Step 37 🔧 M  `DigestService` を `db=DatabaseManager` 必須化
- 場所: `src/services/digest_service.py:51-57`
- 変更: `db: Any` 必須化、`_BOOK_STORE` 削除
- `generate_digest` の finally ブロック (line 202-211) を `_save_digest_db` 呼び出しのみに整理
- コミット: `feat(digest): require db, remove in-memory store`

### Step 38 🔧 S  `easy_mode.py:310, 320` の `db = get_db_manager()` を DI 化
- FastAPI `Depends(get_db)` に置換 (既存パターン踏襲)
- コミット: `refactor(router): gacha/digest use Depends(get_db)`

### Step 39 🔧 S  Router の `ValueError → HTTPException(400)` 統一
- 場所: `routers/easy_mode.py:305-340`
- 各 endpoint に `try/except ValueError as e: raise HTTPException(400, str(e))` を追加
- 既存 `promote_endpoint` の 404 パターンを踏襲
- コミット: `fix(router): map ValueError to 400 in gacha/digest`

### Step 40 ✏️ S  `test_gacha_service_requires_db` 追加
- `GachaService(llm=mock, db=None)` → ValueError
- コミット: `test(gacha): db is required`

### Step 41 ✏️ S  `test_digest_service_requires_db` 追加
- 同上
- コミット: `test(digest): db is required`

### Step 42 ✏️ M  `test_gacha_api_value_error_400` 追加
- リクエスト `genre=""` → 400
- コミット: `test(gacha): api maps validation to 400`

### Step 43 🔧 M  `DigestService.generate_suggestions` を実 LLM 呼び出しに
- 場所: `digest_service.py:34-41`
- 変更: `DigestService` のメソッド化 (`self.llm_service.generate_text(purpose="suggestions", prompt=...)`)
- module-level `generate_suggestions` は deprecation warning 残して後方互換
- コミット: `feat(digest): real LLM suggestions`

### Step 44 ✏️ S  `test_digest_suggestions_uses_llm` 追加
- `DigestService(llm=mock_llm, db=mock_db).generate_suggestions(...)` → mock_llm.generate_text が呼ばれた
- コミット: `test(digest): suggestions hits LLM`

### Step 45 ✏️ S  既存 `test_gacha_api_success` のモック整理
- AsyncMock を `LLMService` 経由に統一、`db` フィクスチャ追加
- コミット: `test(gacha): clean up mocks`

### Step 46 ✏️ S  既存 `test_digest_api_success` のモック整理
- 同上
- コミット: `test(digest): clean up mocks`

---

## フェーズ H: 仕上げ (Day 10-12)

### Step 47 📚 S  Issue #5/#6/#7 完了チェックリスト更新
- 該当 issue に各 Step 番号リンクを貼る
- コミット: なし (GitHub UI)

### Step 48 ✏️ M  CI パイプラインでの実行確認
- `pytest tests/test_unified_pipeline.py tests/test_illustration_agent.py tests/test_easy_mode_api.py -v` をローカル + CI で実行
- カバレッジ計測: `pytest --cov=src/services/pipeline_steps --cov=src/services/image_service --cov=src/services/gacha_service --cov=src/services/digest_service`
- コミット: `chore(ci): verify pipeline+illustration+easy_mode suites`

---

## 実装順序サマリ (最短経路)

```
Day 1-2 : Step 1-4  (基盤)
Day 2-3 : Step 5-12 (IllustrationStep 改修 + テスト)
Day 3-4 : Step 13-18 (MarketingStep 3 段フォールバック)
Day 4-5 : Step 19-24 (Catharsis/Package)
Day 5-7 : Step 25-34 (挿絵ルータ DI + Huey 化 + E2E)
Day 8-10: Step 35-46 (Gacha/Digest 永続化 + 実 LLM 化)
Day 10-12: Step 47-48 (仕上げ)
```

合計: 約 12 営業日 (約 2.5 週)。元工数見積もり「中 (2 週)」と整合。

## 低性能 LLM 向けの実装 Tips

1. **各 Step は独立してコミット可能** にする。途中で壊れても `git revert` 1 つで戻せる
2. **テストは既存 AsyncMock パターンをそのまま踏襲** する (`test_unified_pipeline.py:23-80` の `MockReporter` / `MockEngine` を再利用)
3. **DI 変更は小さく**。`engine.illustration_agent` のような「既存インスタンスを再公開」レベルにとどめ、新規 DI コンテナは作らない
4. **Huey タスクは `immediate=True` モード前提でテスト**。Redis 未起動環境でも CI が通る
5. **文字列補間 / f-string 以外の構文を極力増やさ** ない (Python 3.10 環境想定)
6. **1 Step = 1 ファイル = ~20 行差分** に収める。レビューしやすくロールバック容易
