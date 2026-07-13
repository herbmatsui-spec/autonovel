# 覇権小説自動生成ツール v3.0 — 懸念点解消のための 36ステップ実装計画書

## 目的
中立的技術評価レポート（総合スコア 4.53/5.0）で挙がった 6 つの懸念を、
**「低性能な LLM でも着実に実装可能な粒度」** へ分解した実行計画。
各ステップは **1ユニット = 1取込み = 1検証** を基本とする。

## 6 懸念 → ステップ対応表

| 懸念 # | 内容                               | 対応ステップ |
|--------|------------------------------------|--------------|
| 1      | 手書き DI コンテナ                  | 1–7          |
| 2      | プロンプトテンプレート 100+ ファイル | 8–13         |
| 3      | Gemini 依存度高                     | 14–18        |
| 4      | StateGraph チェックポイント肥大化   | 19–24        |
| 5      | Streamlit 状態管理複雑性            | 25–30        |
| 6      | NCS スコア等 主観指標               | 31–36        |

---

# 懸念 1: 手書き DI コンテナ標準化 (Steps 1–7)

## Step 1 — 現状 DI 構造の静的解析・依存グラフ抽出
**目的**: 移行前スナップショット取得。バグ退避。
**実施**:
1. `python -m scripts.dump_di_graph` スクリプト新設（`scripts/dump_di_graph.py`）:
   - `src/core/container.py` の `AppContainer` クラス属性を `inspect` で列挙
   - 各 Provider の `cls_or_callable` / `args` / `kwargs` を再帰的に走査
   - `dot` 形式で `docs/di_graph_<date>.dot` を出力
2. 既存バグ確認: `container.py:144-203` に存在する `LazyProvider` の末尾に紛れ込んだ
   `SingletonProvider` クラス断片（`def __init__` のみ存在・`class` 宣言無し）を
   **現状維持のまま記録**（Step2 で措置）
3. `pyreverse -o png src/core/container.py` で现在のクラス図を保存
**検証**: `docs/di_graph_<date>.dot` が生成され、`pyreverse` PNG が参照可能。
**成果物**: `scripts/dump_di_graph.py`, `docs/di_graph_<date>.dot`, `docs/di_class_diagram.png`

## Step 2 — SingletonProvider クラス宣言復元（バグ修正）
**目的**: 現状の段階的リファクタ継続を可能にする安全網。
**実施**:
1. `src/core/container.py:144` の `@property def provider` 直後、
   `clear_all_singletons()` の後に `class SingletonProvider:` 宣言を差し戻す。
2. LazyProvider 末尾に残存していた `cls_or_callable` ~ `provider` ブロックを
   `SingletonProvider` クラスの本体へ移動。
3. 既存の unit test `tests/unit/test_container.py` が通ることを確認。
**検証**:
- `python -c "from src.core.container import SingletonProvider; SingletonProvider(print)"`
- `pytest tests/unit/test_container.py -q`
**成果物**: `src/core/container.py`（修正版）

## Step 3 — dependency-injector ライブラリ導入検証（スモークテスト）
**目的**: 移行先が動作するための最小検証。
**実施**:
1. `requirements.txt` へ `dependency-injector>=4.41` 追加。
2. `pip install dependency-injector` を venv 上で実行。
3. `scratch/di_smoke.py` 新設:
   ```python
   from dependency_injector import containers, providers
   class S(containers.DeclarativeContainer):
       v = providers.Singleton(lambda: "ok")
   assert S.v() == "ok"
   ```
4. スモーク実行 `python scratch/di_smoke.py`。
**検証**: 標準出力に `ok`。
**成果物**: `scratch/di_smoke.py`, `requirements.txt`（追記）

## Step 4 — 新 `src/core/di_v2.py` の作成（並行稼働用新コンテナ）
**目的**: 旧コンテナを破壊せず新コンテナを並行構築。
**実施**:
1. `src/core/di_v2.py` 新設:
   ```python
   from dependency_injector import containers, providers
   class AppContainerV2(containers.DeclarativeContainer):
       config = providers.Configuration()
       db = providers.Singleton(...)
       llm_factory = providers.Singleton(...)
       # ... 旧 AppContainer のプロパティを順移植
   ```
2. 旧 `AppContainer` の各プロパティ 1:1 対応で新設（機能差分無し）。
3. **未 wiring**: 旧 `AppContainer` の利用者へは一切影響しない。
**検証**: `python -c "from src.core.di_v2 import AppContainerV2; print(dir(AppContainerV2))"`
**成果物**: `src/core/di_v2.py`

## Step 5 — `AppContainerV2` の単体テスト新設
**目的**: 旧と等価であることを保証。
**実施**:
1. `tests/unit/test_di_v2.py` 新設（`tests/unit/test_container.py` のアサーションを複製）。
2. 各プロバイダの解決成功、override / reset 挙動、lazy 解決、Singleton同一性 を検証。
3. 旧テストの mock を流用。
**検証**: `pytest tests/unit/test_di_v2.py -q` が全件 GREEN。
**成果物**: `tests/unit/test_di_v2.py`

## Step 6 — 段階的切り替え（FeatureFlag 制御）
**目的**: 実行時フラグで旧or新を選択しロールバック容易化。
**実施**:
1. `config/project_context.py` へ `use_di_v2: bool = False` 設定を追加。
2. 新ヘルパ `src/core/get_container.py` 新設:
   ```python
   def get_container():
       from config.project_context import ProjectContext
       if ProjectContext.get_setting("use_di_v2", False):
           from src.core.di_v2 import AppContainerV2
           return AppContainerV2()
       from src.core.container import AppContainer
       return AppContainer
   ```
3. 既存の `AppContainer` 直接参照 30箇所超を `search & replace` で `get_container()` へ置換。
4. 旧 `AppContainer` を stale 扱い（削除しない）。
**検証**:
- デフォルト（`use_di_v2=False`）で `streamlit run app.py` 起動成功。
- `use_di_v2=True` でも同じ起動・Easy Mode 完結。
**成果物**: `src/core/get_container.py`, 設定追加、置換 diff

## Step 7 — 旧コンテナ廃止と `_ALL_SINGLETONS` に依存しない依存グラフ可視化
**目的**: 最終的に単一化し循環検知を自動化。
**実施**:
1. `use_di_v2=True` を既定に変更。
2. `scripts/dump_di_graph.py` を V2 対応（`providers.Singleton` を走査）。
3. `dependency-injector` 組込の `containers.DynamicContainer.providers` から
   `graphviz` を用いて SVG 生成（`docs/di_graph_v2.svg`）。
4. CI に `scripts/dump_di_graph.py --check-cycles` を追加、循環あれば非ゼロ終了。
5. 旧 `src/core/container.py` は `archive/legacy_scripts/` へ移動。
**検証**: CI の当該ジョブ GREEN を確認・SVG 生成。
**成果物**: `scripts/dump_di_graph.py`（V2対応版）, `docs/di_graph_v2.svg`

---

# 懸念 2: プロンプトレジストリ観測性 (Steps 8–13)

## Step 8 — 現状プロンプト目録作成
**目的**: 141 ファイルを俯瞰。
**実施**:
1. `scripts/inventory_prompts.py` 新設:
   - `prompts/` を再帰走査
   - ファイル毎: 行数・変数数 (Jinja2 `{{var}}` の抽出)・`META:` ブロック有無
2. 出力 `docs/prompts_inventory.csv`。
**検証**: CSV が生成され `wc -l` で行数確認（≈140行）。
**成果物**: `scripts/inventory_prompts.py`, `docs/prompts_inventory.csv`

## Step 9 — `PromptRegistry` インタフェース新設
**目的**: 既存 `PromptManager` を wrap しメトリクス収集口を設ける。
**実施**:
1. `src/services/prompt_registry.py` 新設:
   ```python
   class PromptRegistry:
       def __init__(self, pm): self._pm = pm; self._metrics = {}
       def get(self, name, **vars) -> str:
           t0 = perf_counter(); body = self._pm.get_template(name).render(**vars)
           self._metrics[name] = self._metrics.get(name, {"hits":0,"ms":0.0})
           self._metrics[name]["hits"] += 1
           self._metrics[name]["ms"] += (perf_counter()-t0)*1000
           return body
       def metrics(self) -> dict: return dict(self._metrics)
   ```
2. 関連 I/F 定義のみ（実装置換は次 step）。
**検証**: `python -c "from src.services.prompt_registry import PromptRegistry"` が成功。
**成果物**: `src/services/prompt_registry.py`

## Step 10 — `PromptManager` を wrap して DI に登録
**目的**: 実配線。
**実施**:
1. `src/core/container.py` (V2) へ:
   ```python
   pm_registry = providers.Singleton(PromptRegistry, pm)
   ```
2. AUDITOR や PlanningAgent の引数名を `pm` から `pm_registry` に段階変更。
   ただし旧 `pm` シグニチャ互換のため `PromptRegistry.__getattr__` で `PromptManager` へ転送。
3. `src/agents/*.py`（約10箇所）の import 置換。
**検証**: `pytest tests/unit -q` 全 GREEN。UI 起動でプロンプト取得エラー無し。
**成果物**: DI 追加、agent import 置換 diff

## Step 11 — メトリクス永続化（SQLite log テーブル）
**目的**: ヒット率・レンダ時間を定量観測。
**実施**:
1. `alembic/versions/<ts>_add_prompt_usage_log.py` 新設:
   ```sql
   CREATE TABLE prompt_usage_log (
     id INTEGER PK, template_name TEXT, hits INTEGER,
     render_ms REAL, recorded_at TIMESTAMP
   );
   ```
2. `PromptRegistry.flush_metrics()` を5分ごとに呼ぶ APScheduler ジョブ登録
   （`src/services/prompt_metrics_collector.py`）。
3. DI へ `prompt_metrics_collector` を Singleton 登録。
**検証**: Alembic upgrade 成功、SELECT `prompt_usage_log` で行が増加している。
**成果物**: Alembic migration, `src/services/prompt_metrics_collector.py`

## Step 12 — UI ダッシュボード実装
**目的**: 可視化。
**実施**:
1. `streamlit_app/controllers/admin/prompt_metrics.py` 新設:
   - `select * from prompt_usage_log order by render_ms desc` を棒グラフ化
   - `select template_name, sum(hits) group by` で上位 20 をテーブル
2. `pages_config.py` の Advanced Mode へ "Prompts Metrics" ページを追加。
**検証**: UI 表示で3テンプレ以上のメトリクスが可視化される。
**成果物**: `streamlit_app/controllers/admin/prompt_metrics.py`, pages_config 追記

## Step 13 — ホットリロード検証スクリプト
**目的**: 開発中のプロンプト変更を再起動不要化。
**実施**:
1. `PromptManager` に `watch=True` モード追加（`watchdog` 利用）。
2. ファイル変更時 `PromptRegistry` が保持キャッシュを invalidate するよう `clear(name)` 追加。
3. `scripts/watch_prompts.py` で監視 → Streamlit の再描画走破。
4. README "開発Tips" 節に記載。
**検証**: プロンプトを書換え―Streamlit UI の出力が即時変わることを目視確認。
**成果物**: `scripts/watch_prompts.py`, `PromptRegistry.clear(name)`

---

# 懸念 3: Gemini 依存度高 (Steps 14–18)

## Step 14 — `provider_factory` 設定見直し
**目的**: プロバイダ選択条件を明文化。
**実施**:
1. `src/llm/provider_factory.py` を読解し、モデル名→プロバイダ解決表を作成。
2. `docs/llm_routing_table.md` に表として保存。
3. 単体テスト `tests/unit/test_provider_routing.py` 新設（既存ルールをパラメータ化）。
**検証**: pytest GREEN。README にもルーティング方法へのリンクを追記。
**成果物**: `docs/llm_routing_table.md`, `tests/unit/test_provider_routing.py`

## Step 15 — モックプロバイダ（オフライン）完成
**目的**: CI / スモークテストで Gemini 不要化。
**実施**:
1. `src/llm/mock_provider.py` 新設:
   - 事前 fixture JSON を返す `generate_json` / `generate_text`
2. `config/settings.toml` へ `[llm] default_provider="mock"` を許可。
3. `ProjectContext` で環境変数 `LLM_PROVIDER=mock` を解釈。
**検証**: `LLM_PROVIDER=mock python demo.py` が成功（API key 無し）。
**成果物**: `src/llm/mock_provider.py`, settings 拡張

## Step 16 — vLLM / Ollama プロバイダスタブ
**目的**: OSS ローカル LLM の経路整備。
**実施**:
1. `src/llm/openai_compat_provider.py` 新設:
   - `base_url` 引数で vLLM/Ollama エンドポイントを指せる OpenAI 互換薄ラッパ
2. `provider_factory.py` へルート追加（model の prefix で `vllm:`/`ollama:` 判定）。
3. Stub 実装まででベンダ連携動作検証は次ステップ。
**検証**: `tests/unit/test_provider_routing.py` に vllm/ollama prefix を追加し GREEN。
**成果物**: `src/llm/openai_compat_provider.py`, factory 拡張, テスト追加

## Step 17 — スモークテストスイート新設
**目的**: 各プロバイダで一貫して動くテスト。
**実施**:
1. `scripts/smoke_llm.py` 新設:
   - `generate_text` 1件 → 文字列長 > 0 を assert
   - `generate_json` 1件 → `response_schema` 通りであることを assert
2. CLI 引数 `--provider {mock,gemini,openai,vllm,ollama,openai_compat}` で切替。
3. CI に `mock` のみを登録（他は手動）。
**検証**: `python scripts/smoke_llm.py --provider mock` 成功。CI 通過。
**成果物**: `scripts/smoke_llm.py`, CI workflow 編集

## Step 18 — Gemini フォールバック実パス検証
**目的**: レポートの「未検証」を埋める。
**実施**:
1. `tests/integration/test_gemini_fallback.py` 新設:
   - Gemini 側で 429 を意図的に起こし `AdaptiveCooldown` 経路→OpenAI へ切替を検証
   - OpenAI mock を使用し実際の HTTP を叩かない
2. この試験は CI で SKIP 扱い、`run_integration_loop.py` からのみ実行。
**検証**: 手動実行で「OpenAI への切替」ログが1件以上出る。
**成果物**: `tests/integration/test_gemini_fallback.py`

---

# 懸念 4: StateGraph チェックポイント永続化 (Steps 19–24)

## Step 19 — チェックポイントサイズ測定
**目的**: 連載時の肥大化を定量化。
**実施**:
1. `scripts/measure_checkpoint.py` 新設:
   - `MemorySaver` の状態 dict の直列化サイズを `len(pickle.dumps(...))` 計測
   - 1話生成ごとの delta を `docs/checkpoint_growth.csv` に追記
2. writing_langgraph のノード完了フックを利用してサンプリング。
**検証**: CSV が生成される、行数がノード数と一致。
**成果物**: `scripts/measure_checkpoint.py`, CSV

## Step 20 — `SqliteSaver` 導入（langgraph）
**目的**: 永続化への移行基盤。
**実施**:
1. `requirements.txt` に `langgraph[sqlite]>=0.2` を追記。
2. pyproject.toml 互換性確認。
3. スモーク `scratch/sqlite_saver_smoke.py` で `AsyncSqliteSaver.from_conn_string("sqlite:///./scratch/saver.db")` 動作確認。
**検験**: scratch スクリプト成功、`scratch/saver.db` に `checkpoints` テーブル存在。
**成果物**: `scratch/sqlite_saver_smoke.py`, requirements 追記

## Step 21 — `writing_langgraph.py` の checkpointer 切替化
**目的**: 旧 `MemorySaver` を抽象化し選択可能に。
**実施**:
1. `WritingLangGraph.__init__` へ `checkpointer: Optional[BaseCheckpointSaver] = None` 追加。
2. 指定無し時 `MemorySaver()` を使用（後方互換）。
3. 新モジュール `src/backend/workflows/checkpoint_factory.py` 新設:
   ```python
   def get_checkpointer() -> BaseCheckpointSaver:
       if ProjectContext.get_setting("use_sqlite_saver", False):
           return AsyncSqliteSaver.from_conn_string(...)
       return MemorySaver()
   ```
4. `WritingLangGraph` を構築するサービス（`writing_services.py`）で `get_checkpointer()` 経由取得。
**検証**: 既存テスト GREEN。切り替えフラグで DB にレコードが増加。
**成果物**: `src/backend/workflows/checkpoint_factory.py`, 編集3ファイル

## Step 22 — `plot_langgraph.py` 同様適用
**目的**: Plot 側も永続化。
**実施**:
1. Step 21 と同様の変更を `plot_langgraph.py`（現状 `MemorySaver` 無しでも動作）へ適用。
2. 任意で `checkpointer` を受け入れるインタフェースへ拡張。
**検証**: 既存テスト GREEN。
**成果物**: `plot_langgraph.py` 編集

## Step 23 — クラッシュリカバリエンドポイント
**目的**: 中断からの再開機能。
**実施**:
1. `src/api` へ `POST /workflow/resume?thread_id=<uuid>` エンドポイント新設。
2. `langgraph` の `ainvoke(..., config={"configurable": {"thread_id": ...}})` で再開。
3. `streamlit_app/controllers/writing.py` の「中断した生成を再開」ボタンから呼出。
4. UI は `UIStateStore.active_job_ids` にある `run_key` を thread_id として扱う。
**検証**: 中断後ブラウザリロード→ボタンで続きから生成される（手動）。
**成果物**: エンドポイント新設、UI ボタン追記

## Step 24 — 古いチェックポイントの GC
**目的**: 永続化に伴う肥大化抑制。
**実施**:
1. 新テーブル `checkpoint_ttl` を持つ migration。
2. 24h 以上経過したスレッドは `prune_checkpoints.py` で削除。
3. APScheduler の日次ジョブで実行。
**検証**: テスト用に過去日時のレコードを INSERT → prune 実行 → 削除されている。
**成果物**: `crud` migration, `scripts/prune_checkpoints.py`

---

# 懸念 5: フロントエンド状態単一化 (Steps 25–30)

## Step 25 — Streamlit 二重管理の実態整理
**目的**: `st.fragment` と `UIStateStore` の重複範囲を可視化。
**実施**:
1. `streamlit_app/` 配下で `@st.fragment` 使用箇所を grep 列挙。
2. `streamlit_app/controllers/*` で `st.session_state[...]` 直接参照箇所を列挙。
3. `docs/state_management_audit.md` に表形式で出力（ファイル・行・キー名）。
**検証**: 表が 30 行以上生成される。
**成果物**: `scripts/audit_state_usage.py`, `docs/state_management_audit.md`

## Step 26 — 直接 `st.session_state` 参照を `UIStateStore` 経由へ縮小
**目的**: SSOT 化の第一歩。
**実施**:
1. `UIStateStore` に未対応キーがあれば `AppRuntimeState` へ追加。
2. 表に列挙した 30 箇所を 5箇所ずつ `UIStateStore.update_runtime(...)` 経由へ置換。
3. 段階 PR または段階 commit 単位で実施。
**検証**: 残存 `st.session_state[` 数が前回比で半減していることを grep で確認。
**成果物**: 編集 diff（5ファイル程度/バッチ）

## Step 27 — `@st.fragment` 利用規約化
**目的**: 何に使うべきか明文化。
**実施**:
1. `docs/adr/0001-st-fragment-policy.md` 新設（ADR フォーマット）:
   - fragment は「局所再描画のみ」に使用
   - fragment 内で `UIStateStore.update_*` を呼ばない（fragment → 親描画が skip される為）
2. 既存 fragment 違反箇所を `grep` で列挙。
**検証**: ADR が存在し、違反箇所数がリスト化されている。
**成果物**: `docs/adr/0001-st-fragment-policy.md`

## Step 28 — Zustand 風 単一 Store のプロトタイプ
**目的**: 将来は React/Frontend 側へ。現段階は Streamlit 内で模倣。
**実施**:
1. `frontend/src/store/novelStore.ts` 新設（zustand 既存なので）:
   - `api_state: 'idle' | 'running' | 'error'`
   - `app_mode`, `selected_desires` 等
2. OpenAPI 経由で Streamlit と状態同期するのは後続ステップ。
3. 現段階は「型だけ合せる」まで。
**検証**: `npm run -w frontend typecheck` が GREEN。
**成果物**: `frontend/src/store/novelStore.ts`

## Step 29 — `UIStateStore` の Observer を Async Queue 化
**目的**: callback 例外で全体停止しない。
**実施**:
1. `UIStateStore._notify` を `asyncio.Queue` 経由で発火。
2. 例外時は toast 表示のみ（現状ロギング）。
3. `subscribe` で `async` callback を許可。
**検証**: 既存 UI テスト GREEN、例外時ロギングのみで再描画続行。
**成果物**: `src/core/state/ui_store.py` 編集

## Step 30 — 移行済みフラグ管理とドキュメント化
**目的**: 状態管理の SSOT 完結宣言。
**実施**:
1. CI に `warnings.warn` 発生を grep、`st.session_state[` 直接参照が 5箇所未満なら PASS。
2. `docs/state_management_audit.md` を最終状態に更新。
3. README へ「状態管理概要」セクション追記（3段落）。
**検証**: CI check 追加 GREEN、README 更新確認。
**成果物**: CI workflow, README, audit 更新版

---

# 懸念 6: NCS/品質指標の校正パイプライン (Steps 31–36)

## Step 31 — 人間評価 CSV スキーマ設計
**目的**: 自動スコア×人間評価 相関分析の土台。
**実施**:
1. `schemas/ncs_calibration.py` 新設:
   ```python
   class HumanEvalRecord(BaseModel):
       episode_id: str; reader_id: str
       star_rating: int  # 1-5
       nps: int           # -100..100
       tags: list[str]
       comment: str
   ```
2. 読込 API（`/admin/import_human_eval`）のスタブ設計のみ。
**検証**: pydantic validation 成功（pytest）。
**成果物**: `schemas/ncs_calibration.py`

## Step 32 — DB マイグレーション
**目的**: 人間評価レコード保存。
**実施**:
1. `alembic/versions/<ts>_add_human_eval.py` 新設:
   - `human_eval` テーブル
   - FK: `episode_id` → `episodes.id`
2. `models/db.py` へ SQLAlchemy モデル `HumanEval` 追加。
3. CRUD `src/services/human_eval_repo.py` 新設。
**検証**: `alembic upgrade head` 成功、CRUD 単体テスト GREEN。
**成果物**: migration, model, repo

## Step 33 — 自動 NCS スコア抽出の安定化
**目的**: 評価対象 episode に紐付く NCS を集計。
**実施**:
1. `narrative_scoring_service.py` の `score` 戻り値を pydantic `NarrativeScore` 化。
2. `episodes` テーブルにも `ncs` カラム追加（migration）。
3. 生成完了時に `episodes.ncs` を UPSERT。
**検証**: `SELECT episode_id, ncs FROM episodes LIMIT 10` で NULL が半数未満。
**成果物**: service 編集, migration, model

## Step 34 — 相関分析スクリプト
**目的**: 相関係数を算出。
**実施**:
1. `scripts/ncs_correlation.py` 新設:
   - `human_eval` と `episodes.ncs` を JOIN
   - Spearman / Pearson で star_rating, nps 対 ncs の係数を算出
2. `docs/ncs_calibration_report.md` へ出力（手動実行）。
**検証**: スクリプト実行で数値が2つ以上出る。
**成果物**: `scripts/ncs_correlation.py`, report md

## Step 35 — 閾値校正スクリプト
**目的**: 実運用に合う閾値へ再設定。
**実施**:
1. `scripts/ncs_threshold_calibrate.py` 新設:
   - NCS 分布から p25/p50/p75 を計算
   - `<config/settings.toml>` の `[writing] ncs_threshold_early_exit` を推奨値で書き戻す
2. `ConfigValidator` が推奨値範囲外で warning を出すよう `config/validator.py` に照合追加。
**検証**: スクリプト実行で設定ファイルが更新される、_validator warning が表示対象で出る。
**成果物**: `scripts/ncs_threshold_calibrate.py`, validator 拡張

## Step 36 — UI 校正ダッシュボード
**目的**: 運用者自身で分析可能に。
**実施**:
1. `streamlit_app/controllers/admin/ncs_calibration.py` 新設:
   - 散布図 (NCS vs star_rating)
   - 閾値推奨値を `st.metric` 表示
   - 「設定を反映」ボタンで `settings.toml` へ上書き
2. Advanced Mode の Admin 配下に "NCS Calibration" ページ追加。
**検証**: 手動起動後、散布図が表示され 3 件以上プロットされる。
**成果物**: controller, pages_config 追記

---

# 進行管理

- 各 Step の完了は **専用の GitHub Issue / ローカル TODO** で管理し、コミットメッセージに `[step N]` プレフィクスを付与。
- 各 Step 完了判定:
  - 該当 Step の **検証** コマンドが GREEN
  - 該当 Step の **成果物** が存在（`Test-Path` / `git status`）
- 全 36 Step 完了後、再評価レポートを実施しスコアアップを定量確認。

# 高性能LLM不要の粒度設計理由

各 Step は **「ファイル 1–3 / 関数 1–5 / 行数 100 未満」** を単位としている。
理由:
1. 低性能 LLM でも「与えられた diff パッチ・既存テスト」で文脈完結可能。
2. 1 Step = 1 commit にできるため、レビュー負荷を均一化。
3. CI が途中で失败しても次 Step へ進められるよう、現状 OK な状態を保存してから着手する様式を定義。

# マイルストーン概観

| Milestone | Steps | 想定工数 |
|-----------|-------|----------|
| M1: DI 標準化         | 1–7   | 3–4d |
| M2: Prompt 観測性     | 8–13  | 3–4d |
| M3: LLM 多プロバイダ  | 14–18 | 2–3d |
| M4: Checkpoint 永続化 | 19–24 | 4–5d |
| M5: UI 状態単一化     | 25–30 | 3–4d |
| M6: NCS 校正          | 31–36 | 4–5d |
| **合計**              | **36** | **19–25d** |

---

# 前提・注意事項

- 本計画は **動作する現状を壊さない** を第一とする。
- 旧実装は `archive/legacy_scripts/` へ退避させ、即削除しない。
- 各 Step 前には必ず `git status` / `git diff` で作業範囲を確認し、コンテキスト混入を防ぐ。
- `requirements.txt`・`alembic`・`schemas/app_state.py` 等の共通資産を触る Step では、
  Step 単位でブランチを分離し、少なくとも1ユニットテストを GREEN に保つ。
- CI が未整備の lint/test は `run_tests.bat` で代替可。
