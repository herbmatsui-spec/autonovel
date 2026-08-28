# novel_50ep の src 統合（②）＋ ドメイン・イベントバス（③）実装計画

## 0. 概要

`novel_50ep/` は `src/` を一切 import せず（grep で 0 件）、`MockLLMGenerator` と独自 config/CSV で完結している。これを `src/prototype/` として `src` 基盤の「薄いアダプタ」に降格し、同時に機能間をドメイン・イベントバスで疎結合直結する。36 ステップ、低性能 LLM でも 1 ステップずつ pytest 緑で進められる。

確認済インターフェース：
- `LLMGenerateResultProxy.generate_text(prompt, ...)` （`src/core/llm_gateway.py:132`）
- `QualityScorer.score_all(text)` async → `QualityMetricsReport`（`src/services/quality_scorer.py:194`）
- `NarrativeScoringService.score(content, schema)` async（`src/services/narrative_scoring_service.py:14`）
- `AffinityTracker.update_from_text(text)`（`src/services/affinity_tracker.py:38`）
- `EroticQualityScorer.score(text)`（`src/agents/erotic/evaluator.py:113`）
- `MiscRepository.save_internal_state(key, value)` / `get_internal_state(key)`（`src/backend/database/repositories/misc.py:117`）— 伏線永続に再利用
- `src/shared/event_bus.py` は UI 型の再公開のみ（domain バスは別新設）

---

## Phase A：novel_50ep を src アダプタにする（ステップ 1〜18）

### ステップ 1
- 対象：`src/prototype/__init__.py`（新規）
- 目的：統合先パッケージを作る。
- 作業：空の `__init__.py` を作成。
- 受入：`import src.prototype` が通る。

### ステップ 2
- 対象：`src/prototype/llm_adapter.py`
- 目的：`MockLLMGenerator` を本番 LLM へ繋ぐ。
- 作業：`class GatewayLLMGenerator: def generate(self, prompt, target_chars=0, **kw): return await LLMGenerateResultProxy().generate_text(prompt, ...)`。既存 `MockLLMGenerator` と同じ `generate(prompt, target_chars, part_id, ep, cliff)` シグネチャを維持。
- 受入：mock provider で文字列を返す（pytest）。

### ステップ 3
- 対象：`tests/unit/test_prototype_llm.py`
- 目的：ステップ2を固定。
- 作業：`GatewayLLMGenerator().generate("p", 100)` が str を返ることを assert（LLM はモック注入）。
- 受入：pytest 通る。

### ステップ 4
- 対象：`src/prototype/score_adapter.py`
- 目的：`ScoreReviewer` を本番スコアラへ委譲。
- 作業：`class PrototypeScorer: async def score(self, ep, text): q=await QualityScorer().score_all(text); n=await NarrativeScoringService().score(text, None); return EpisodeScore(ep, pacing=q.pacing, emotion=..., world=..., cliff=..., total_score=合成値, details={...})`。`EpisodeScore` は `novel_50ep/score_reviewer.py` の dataclass を再利用。
- 受入：pytest（mock）で `EpisodeScore` を返す。

### ステップ 5
- 対象：`tests/unit/test_prototype_score.py`
- 目的：ステップ4を固定。
- 作業：両サービスを mock に差し替え、`score()` が `total_score` を持つことを assert。
- 受入：pytest 通る。

### ステップ 6
- 対象：`src/prototype/foreshadow_adapter.py`
- 目的：伏線を DB へ永続。
- 作業：`class PersistentForeshadowManager(ForeshadowManager): def persist(self, book_id, branch_id, repo): repo.save_internal_state(f"fs:{book_id}:{branch_id}", self.foreshadows)` と `load_persistent(...)` を追加。CSV 動作は維持。
- 受入：pytest（mock repo）で save→load 一致。

### ステップ 7
- 対象：`tests/unit/test_prototype_foreshadow.py`
- 目的：ステップ6を固定。
- 作業：登録→persist→別インスタンスで load_persistent が同一内容。
- 受入：pytest 通る。

### ステップ 8
- 対象：`src/prototype/polish_adapter.py`
- 目的：`polish` を本番修正へ。
- 作業：`def polish(text, scene=None, hub=None): from src.agents.erotic.enhancer import EroticEnhancer; out=EroticEnhancer().post_process_erotic_content(text, scene); if hub and hub.continuity_violations: out="以下の矛盾を修正:"+hub.report()+"\n"+out; return out`。既存 `novel_50ep/polish_tool.py` の前処理を流用。
- 受入：pytest で違反時に文言付与。

### ステップ 9
- 対象：`tests/unit/test_prototype_polish.py`
- 目的：ステップ8を固定。
- 作業：violations ありで戻り文字列に文言含む。
- 受入：pytest 通る。

### ステップ 10
- 対象：`novel_50ep/generator.py`
- 目的：generator が本番 LLM を使う。
- 作業：`NovelGenerator` が `GatewayLLMGenerator` を優先し、import 不可時は `MockLLMGenerator` へ fallback（既存 try/except を拡張）。
- 受入：既存テスト緑。

### ステップ 11
- 対象：`novel_50ep/score_reviewer.py`
- 目的：scorer を委譲。
- 作業：`ScoreReviewer.score` 内で `src.prototype.score_adapter.PrototypeScorer` を呼ぶよう書き換え（CSV 出力は維持）。
- 受入：pytest 緑。

### ステップ 12
- 対象：`novel_50ep/foreshadow_manager.py`
- 目的：永続化を委譲。
- 作業：CSV ラッパのまま、`PersistentForeshadowManager` を継承・利用。
- 受入：pytest 緑。

### ステップ 13
- 対象：`novel_50ep/polish_tool.py`
- 目的：polish を委譲。
- 作業：`polish()` を `src.prototype.polish_adapter.polish` へ転送。
- 受入：pytest 緑。

### ステップ 14
- 対象：`novel_50ep/batch_runner.py`
- 目的：バッチが本番 DB に書く。
- 作業：`--fix-continuity` で `PrototypeScorer`/`PersistentForeshadowManager` 経由で DB 保存。
- 受入：pytest 緑。

### ステップ 15
- 対象：`novel_50ep/tests/test_novel_50ep.py`
- 目的：後方互換を確認。
- 作業：既存テスト全通を確認。
- 受入：pytest 緑。

### ステップ 16
- 対象：`tests/integration/test_prototype_pipeline.py`（新規）
- 目的：Phase A 統合。
- 作業：1 話 generate→score→foreshadow→polish し DB に残る（mock LLM/DB）。
- 受入：pytest 通る。

### ステップ 17
- 対象：`novel_50ep/CONTINUITY_IMPLEMENTATION_PLAN.md`
- 目的：文書整合。
- 作業：ステップ 60/69 を「src/prototype 経由で本番 DB に食い込む」に書き換え。
- 受入：参照矛盾なし。

### ステップ 18
- 対象：`src/backend/workflows/commercial_pipeline.py`（CI）
- 目的：CI で保護。
- 作業：`pytest novel_50ep/tests src/prototype tests/unit/test_prototype_*` を走らせるジョブ追加。
- 受入：CI 緑。

---

## Phase B：ドメイン・イベントバス（ステップ 19〜36）

### ステップ 19
- 対象：`src/shared/domain_event_bus.py`（新規）
- 目的：軽量 pub/sub を作る。
- 作業：`@dataclass DomainEvent: type:str; payload:dict; book_id:int; ep:int`。`class EventBus: _subs={}; def subscribe(self,t,h):...; async def publish(self,t,ev): [await h(ev) for h in _subs.get(t,[])]`。
- 受入：pytest で subscribe→publish 動作。

### ステップ 20
- 対象：`tests/unit/test_domain_event_bus.py`
- 目的：ステップ19を固定。
- 作業：handler が呼ばれ payload を受け取る。
- 受入：pytest 通る。

### ステップ 21
- 対象：`src/shared/domain_event_bus.py`
- 目的：イベント型を定義。
- 作業：`class NarrativeEventType(Enum): EPISODE_WRITTEN/ EPISODE_EVALUATED/ REVISION_REQUESTED`。
- 受入：pytest で enum 参照可。

### ステップ 22
- 対象：`tests/unit/test_domain_event_bus.py`
- 目的：ステップ21を固定。
- 作業：enum 値を assert。
- 受入：pytest 通る。

### ステップ 23
- 対象：`src/prototype/adapters/tension_sub.py`（または既存 adapter）
- 目的：TensionService を購読。
- 作業：`def on_written(hub, ev): hub.tension_curve.append(ev.payload["tension"])` を bus.subscribe(WRITTEN, ...) 登録する関数 `register(bus, hub)`。
- 受入：pytest で hub 更新。

### ステップ 24
- 対象：同上 `affinity_sub.py`
- 目的：AffinityTracker を購読。
- 作業：`on_written` で `AffinityTracker().update_from_text(ev.payload["text"])` → hub.affinity_map 更新。
- 受入：pytest で更新。

### ステップ 25
- 対象：`continuity_sub.py`
- 目的：ContinuityTracker を購読。
- 作業：`on_written` で `feed_continuity(hub, ev.payload["scene"])`。
- 受入：pytest で violations 追加。

### ステップ 26
- 対象：`narrative_sub.py`
- 目的：NarrativeScoringService を購読。
- 作業：`on_written` で `await update_narrative(hub, ep, text)`。
- 受入：pytest で更新。

### ステップ 27
- 対象：`erotic_sub.py`
- 目的：EroticEnhancer を購読。
- 作業：`on_written` で `update_erotic(hub, ep, text)`。
- 受入：pytest で更新。

### ステップ 28
- 対象：`tests/unit/test_subscribers.py`
- 目的：Phase B 前半を固定。
- 作業：WRITTEN  publish で全購読者が呼ばれ hub が埋まる（mock サービス）。
- 受入：pytest 通る。

### ステップ 29
- 対象：`src/prototype/aggregator.py`
- 目的：結果を集約して EPISODE_EVALUATED を出す。
- 作業：`async def aggregate(bus, hub, ev): 全 adapter で hub 更新; await bus.publish(EVALUATED, DomainEvent(payload=hub.to_dict(), ...))`。
- 受入：pytest で EVALUATED が publish される。

### ステップ 30
- 対象：`tests/unit/test_aggregator.py`
- 目的：ステップ29を固定。
- 作業：aggregator 呼びで EVALUATED handler が hub を受け取る。
- 受入：pytest 通る。

### ステップ 31
- 対象：`src/backend/workflows/nodes/master_nodes.py`（call_writing_graph_node）
- 目的：書き込み後にイベント発行。
- 作業：各 ep の `res` 取得後 `await bus.publish(WRITTEN, DomainEvent(book_id, ep, payload={"text":..., "scene":...}))`。
- 受入：pytest で発行される。

### ステップ 32
- 対象：`src/backend/workflows/graphs/master_graph.py`（should_revise_writing）
- 目的：EVALUATED を消費。
- 作業：hub の `continuity_violations` や `affinity_map` 低下を `needs_revision_eps` に加える（Phase1 計画と同一ロジック）。
- 受入：pytest で違反 ep が revise 対象。

### ステップ 33
- 対象：`tests/integration/test_eventbus_flow.py`
- 目的：Phase B 統合。
- 作業：WRITTEN を publish → 全購読 → EVALUATED → revise 判定、を end-to-end 検証。
- 受入：pytest 通る。

### ステップ 34
- 対象：`src/prototype/generator.py`（または既存）
- 目的：プロトタイプ側も発行。
- 作業：Phase A の generator が 1 話書き込み後に `bus.publish(WRITTEN, ...)` するよう拡張（②と③の接続）。
- 受入：pytest でプロトタイプ実行時に購読者動作。

### ステップ 35
- 対象：`novel_50ep/CONTINUITY_IMPLEMENTATION_PLAN.md` と `src/shared/event_bus.py`
- 目的：棲み分けを記述。
- 作業：UI 用 `event_bus.py` と domain `domain_event_bus.py` の違い、および「機能追加＝購読を足すだけ」を明記。
- 受入：文書矛盾なし。

### ステップ 36
- 対象：`src/backend/workflows/commercial_pipeline.py` ＋統合テスト
- 目的：最終保護。
- 作業：Phase A+B の pytest を CI ジョブにまとめ、全購読者動作＋緑を確認。
- 受入：CI 緑。

---

## 付録：依存と成果

```
Phase A(1-18) -> Phase B(19-36)
```
A で `novel_50ep` が `src` の LLM/スコア/DB に初めて食い込み、B で各機能が `EpisodeWritten` を購読して `NarrativeState`(計画①) へ集約、`EpisodeEvaluated` を `MasterGraph` の revise 判定が消費する。機能追加はノード書き換えではなく「購読を足すだけ」になり、結合が生きたまま保たれる。
