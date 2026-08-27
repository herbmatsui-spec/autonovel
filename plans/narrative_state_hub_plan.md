# NarrativeState 共通ハブ実装計画（SSOT 化）

## 0. 概要と狙い

現状、`src/` 内の強化系機能（TensionService・AffinityTracker・QualityScorer・NarrativeScoringService・EroticQualityScorer・連続性/伏線管理）は `report_generator`・`ux_routes`・`_writing` など散在する 1〜2 箇所からしか呼ばれず、互いの結果が合流しない。そのため「好感度低下＋伏線未回収」を review が検知して revise が補正する、といった有機的結合が起きない。

本計画は、全機能が読み書きする単一の `NarrativeState` ハブを SSOT として `MasterGraph` の各ノードに通すことで、データを介した結合を実現する。低性能 LLM でも 1 ステップずつ `pytest` で緑を確認しながら進められるよう 24 ステップに分割する。

依存関係の実シグネチャ（確認済）：
- `AffinityTracker.update_from_text(text, character_name=None) -> List[AffinityData]` / `get_all_affinities()`
- `QualityScorer.score_all(text) -> QualityMetricsReport`（async）
- `NarrativeScoringService.score(content, schema) -> Dict`（async）
- `EroticQualityScorer.score(text) -> EroticQualityReport`
- `TensionService`（base_workflow で注入 / engine の tension_agent で代用）
- `MasterGraphState` は `state.py` の TypedDict（total=False）

---

## Phase 1：ハブの定義（ステップ 1〜6）

### ステップ 1
- 対象：`src/backend/workflows/narrative_state.py`（新規）
- 目的：ハブの入れ物を作る。
- 作業：`@dataclass` の `NarrativeState` を定義。`book_id:int=1`, `branch_id:int=1`, `episodes:Dict[int, dict]={}`, `tension_curve:List[float]=[]`, `affinity_map:Dict[str,float]={}`, `foreshadow_registry:List[dict]=[`, `continuity_violations:List[dict]=[]`, `quality_scores:Dict[int,dict]={}`, `erotic_metrics:Dict[int,dict]={}`, `narrative_scores:Dict[int,dict]={}` を持たせる。
- 受入：`from src.backend.workflows.narrative_state import NarrativeState` がエラーなし。

### ステップ 2
- 対象：`narrative_state.py`
- 目的：シリアライズできるようにする。
- 作業：`to_dict(self)` / `from_dict(cls, d)` を追加（dataclasses.asdict と `cls(**d)` で十分）。
- 受入：`NarrativeState().to_dict()` が dict を返し、`NarrativeState.from_dict(d)` が復元される。

### ステップ 3
- 対象：`narrative_state.py`
- 目的：話単位の更新を安全に行うヘルパを作る。
- 作業：`def upsert_episode(self, ep:int, **fields): self.episodes.setdefault(ep, {}).update(fields)` を追加。
- 受入：`upsert_episode(1, char_count=300)` で `episodes[1]["char_count"]==300`。

### ステップ 4
- 対象：`tests/unit/test_narrative_state.py`（新規）
- 目的：Phase1 を固定。
- 作業：to_dict/from_dict ラウンドトリップと upsert_episode を assert。
- 受入：`pytest tests/unit/test_narrative_state.py` が通る。

### ステップ 5
- 対象：`src/backend/workflows/state.py`
- 目的：`MasterGraphState` にハブ参照を追加（後方互換）。
- 作業：`MasterGraphState` に `narrative: Any` フィールドを追加（total=False なので既存呼び出しは壊れない）。
- 受入：`MasterGraphState` を使う既存テストが緑のまま。

### ステップ 6
- 対象：`tests/unit/test_narrative_state.py`
- 目的：MasterGraphState が hub を受け取れることを確認。
- 作業：`MasterGraphState(narrative=NarrativeState())` が構築できることを assert。
- 受入：pytest が通る。

---

## Phase 2：ハブへ読み書きするアダプタ（ステップ 7〜14）

### ステップ 7
- 対象：`src/backend/workflows/adapters/__init__.py`（新規、空）
- 目的：アダプタ置き場を作る。
- 作業：`adapters/__init__.py` を作成。
- 受入：`import src.backend.workflows.adapters` が通る。

### ステップ 8
- 対象：`adapters/tension_adapter.py`
- 目的：テンションを hub へ書く。
- 作業：`async def update_tension(hub, ep, tension_value:float): hub.tension_curve.append(tension_value); hub.upsert_episode(ep, tension=tension_value)`。
- 受入：呼ぶと `tension_curve` に値が追加される（pytest）。

### ステップ 9
- 対象：`adapters/affinity_adapter.py`
- 目的：好感度を hub へ書く。
- 作業：`def update_affinity(hub, ep, text): from src.services.affinity_tracker import AffinityTracker; a=AffinityTracker(); res=a.update_from_text(text); hub.affinity_map={d.character:d.score for d in res}; hub.upsert_episode(ep, affinity=dict(hub.affinity_map))`。
- 受入：mock テキストで `affinity_map` が更新される。

### ステップ 10
- 対象：`adapters/quality_adapter.py`
- 目的：品質スコアを hub へ書く。
- 作業：`async def update_quality(hub, ep, text): from src.services.quality_scorer import QualityScorer; r=await QualityScorer().score_all(text); hub.quality_scores[ep]=r.__dict__ if hasattr(r,'__dict__') else dict(r); hub.upsert_episode(ep, quality=hub.quality_scores[ep])`。
- 受入：pytest（mock score_all）で `quality_scores[ep]` が埋まる。

### ステップ 11
- 対象：`adapters/narrative_adapter.py`
- 目的：ナラティブ総合評価を hub へ書く。
- 作業：`async def update_narrative(hub, ep, text, schema=None): from src.services.narrative_scoring_service import NarrativeScoringService; r=await NarrativeScoringService().score(text, schema); hub.narrative_scores[ep]=r; hub.upsert_episode(ep, narrative=r)`。
- 受入：pytest で `narrative_scores[ep]` が埋まる。

### ステップ 12
- 対象：`adapters/erotic_adapter.py`
- 目的：官能指標を hub へ書く。
- 作業：`def update_erotic(hub, ep, text): from src.agents.erotic.evaluator import EroticQualityScorer; rep=EroticQualityScorer().score(text); hub.erotic_metrics[ep]={k:getattr(rep,k,None) for k in ('score','intensity','coherence')}; hub.upsert_episode(ep, erotic=hub.erotic_metrics[ep])`。
- 受入：pytest で `erotic_metrics[ep]` が埋まる。

### ステップ 13
- 対象：`adapters/continuity_adapter.py`
- 目的：連続性違反を hub へ蓄積する。
- 作業：`def feed_continuity(hub, scene_dict): from novel_50ep.continuity_tracker import ContinuityTracker`（存在しない場合は `src/agents/erotic/continuity.py` を利用）で tracker を作り `v=tracker.feed(scene_dict); hub.continuity_violations.extend(v)`。tracker は `hub` に `tracker` 属性として保持。
- 受入：不一致シーンで `continuity_violations` に要素が追加される（pytest）。

### ステップ 14
- 対象：`tests/unit/test_narrative_adapters.py`（新規）
- 目的：Phase2 を固定。
- 作業：各アダプタをモックサービスで呼び、hub の対応フィールドが更新されることを assert（tension/affinity/quality/narrative/erotic/continuity の 6 件）。
- 受入：pytest が全て通る。

---

## Phase 3：MasterGraph ノードへの接続（ステップ 15〜20）

### ステップ 15
- 対象：`src/backend/workflows/nodes/master_nodes.py`（`call_plot_graph_node`）
- 目的：ハブを初期化してサブグラフへ渡す。
- 作業：先頭で `hub = state.get("narrative") or NarrativeState(book_id=state.get("book_id",1), branch_id=state.get("branch_id",1))` とし、plot_input の `metadata["narrative_hub"]=hub.to_dict()` に入れ、返り値に `"narrative": hub` を含める。
- 受入：plot 実行後 `state["narrative"]` が存在する（pytest）。

### ステップ 16
- 対象：`master_nodes.py`（`call_writing_graph_node`）
- 目的：各話執筆後に全アダプタで hub を更新。
- 作業：各 ep の `res` 取得後、`text=res.get("draft_content","")` で `await update_quality(hub,ep,text)`, `update_affinity(hub,ep,text)`, `await update_narrative(hub,ep,text)`, `update_erotic(hub,ep,text)`, `feed_continuity(hub, {"ep":ep,"text":text})` を呼ぶ。`bible_state` の代わり/追加として hub も返す。
- 受入：pytest で書き戻し後 `hub.quality_scores`/`hub.affinity_map` 等が埋まる。

### ステップ 17
- 対象：`master_nodes.py`（`call_review_graph_node`）
- 目的：review を hub の文脈で豊かにする。
- 作業：review_input の `metadata` に `hub.to_dict()` を追加し、レビューがテンション/好感度/伏線/連続性違反を参照できるようにする（既存 `bible_state` は維持）。
- 受入：review_input に `narrative_hub` が含まれる（pytest）。

### ステップ 18
- 対象：`src/backend/workflows/graphs/master_graph.py`（`should_revise_writing`）
- 目的：hub シグナルも revise 判定に使う。
- 作業：`hub=state.get("narrative")` があり、`hub.continuity_violations` にその ep の違反、または `affinity_map` が前話より低下している ep があれば `needs_eps` に加える。
- 受入：違反がある ep が revise 対象に入る（pytest）。

### ステップ 19
- 対象：`master_nodes.py`（`revise_writing_node`）
- 目的：rewrite が hub の指摘を補正する。
- 作業：writing_input の `fw_prompt` に、`hub.continuity_violations` および `hub.foreshadow_registry` の未回収を要約して付与。rewrite 後、ステップ 16 と同様に全アダプタで hub を再更新。
- 受入：pytest で再執筆後に hub 違反が減る（mock で検証）。

### ステップ 20
- 対象：`tests/integration/test_narrative_hub_flow.py`（新規）
- 目的：Phase3 の統合を固定。
- 作業：2 話分を `SequentialMasterGraphFallback` で流し、`hub.tension_curve` が 2 点、`hub.affinity_map` が存在、かつ意図的に連続性違反を作った ep が `needs_revision_eps` に入ることを assert。
- 受入：pytest が通る。

---

## Phase 4：永続化と可視化（ステップ 21〜24）

### ステップ 21
- 対象：`state.py` / `master_nodes.py`
- 目的：ハブをメトリクスへ出力。
- 作業：`MasterGraphState` に `narrative_report: Dict` を追加。`call_review_graph_node` の `metrics` に `hub.to_dict()` を `"narrative"` キーで格納して返す。
- 受入：review 結果の `quality_metrics["narrative"]` に hub が入る。

### ステップ 22
- 対象：`src/backend/database/repositories/misc.py`（または既存リポジトリ）
- 目的：hub を跨パイプラインで保持。
- 作業：`save_narrative(book_id, branch_id, hub.to_dict())` / `load_narrative(book_id, branch_id)` を追加（JSON 保存で十分）。
- 受入：save→load で同一 dict が戻る（pytest）。

### ステップ 23
- 対象：`src/backend/routers/system.py`（または適切な router）
- 目的：フロントエンド/外部から hub を見える化。
- 作業：`GET /api/narrative/{book_id}/{branch_id}` を追加し、`load_narrative` の結果を返す。
- 受入：curl/pytest でエンドポイントが hub JSON を返す。

### ステップ 24
- 対象：`novel_50ep/CONTINUITY_IMPLEMENTATION_PLAN.md` と `plans/`
- 目的：全体を記録・相互参照。
- 作業：本計画を `plans/narrative_state_hub_plan.md` に置き、CONTINUITY 文書のステップ 67/68 を「本番は `/api/narrative` と `NarrativeState` ハブを使う」よう書き換え、矛盾を解消。
- 受入：文書間の参照が一致し、Phase1〜4 の pytest が全て緑。

---

## 付録：ステップ間依存

```
Phase1(1-6) -> Phase2(7-14) -> Phase3(15-20) -> Phase4(21-24)
```
各ステップは前ステップの「受入基準」が満たされていれば独立実装可能。ステップ 13 の連続性トラッカーは `novel_50ep.continuity_tracker` が未実装なら `src/agents/erotic/continuity.py` へ差し替え（いずれも同一インターフェース `feed(scene)->violations` を期待）。これにより全機能が `NarrativeState` を介して初めて有機的に結合する。
