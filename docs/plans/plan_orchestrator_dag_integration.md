# Orchestrator → DAGScheduler 統合 実装計画書（全72ステップ）

## 前提条件
- 作業ディレクトリ: `E:\hhh`
- 対象ファイル: `src/agents/orchestrator.py`, `src/backend/tasks/dag_scheduler.py`, `src/backend/tasks/generation_tasks.py`
- 実行前: `git status` でクリーンな状態を確認
- 完了基準: 既存テスト（`pytest tests/ -k orchestrator`）が全パスすること

---

### Phase 0: 現状把握・準備（ステップ1〜6）

**ステップ1** `E:\hhh\src\agents\orchestrator.py` を読み、460行目以降の `run()` メソッド全体を理解する

**ステップ2** `E:\hhh\src\backend\tasks\dag_scheduler.py` を読み、`DAGScheduler.run_dag()` のシグネチャと `task_registry` の使い方を理解する

**ステップ3** `E:\hhh\src\backend\tasks\dag_models.py` を読み、`DAGGraph`, `DAGTaskNode`, `TaskResourceRequirement` の構造を理解する

**ステップ4** `E:\hhh\src\backend\tasks\generation_tasks.py` の `build_novel_generation_dag()` （337行目〜）を参照し、DAG 構築パターンを確認する

**ステップ5** `E:\hhh\src\agents\event_bus.py` を読み、`EventBus.publish_async()` の呼び出し規約を確認する

**ステップ6** ターミナルで `cd E:\hhh && git diff HEAD` を実行し、未コミット変更がないことを確認する

---

### Phase 1: Orchestrator クラス拡張（ステップ7〜18）

**ステップ7** `src/agents/orchestrator.py` の `Orchestrator.__init__` に `dag_scheduler: DAGScheduler | None = None` 引数を追加し、 `self.dag_scheduler = dag_scheduler` で保持する

**ステップ8** `Orchestrator.__init__` に `use_dag_scheduler: bool = False` 引数を追加し、 `self.use_dag_scheduler = use_dag_scheduler` で保持する

**ステップ9** `from_manifest` クラスメソッドのシグネチャに `dag_scheduler: DAGScheduler | None = None` と `use_dag_scheduler: bool = False` を追加する

**ステップ10** `from_manifest` 内で `Orchestrator` インスタンス生成時に `dag_scheduler` と `use_dag_scheduler` を渡すよう修正する

**ステップ11** `Orchestrator` クラスに `_build_dag_graph() -> DAGGraph` プライベートメソッドを新規作成する（空のメソッドでよい）

**ステップ12** `_build_dag_graph` 内で `from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode, TaskResourceRequirement` をインポートする

**ステップ13** `_build_dag_graph` で `DAGGraph(dag_id=f"orch_{self.correlation_id}")` を生成し、変数 `graph` に格納する

**ステップ14** `_build_dag_graph` で `self._ordered_skill_names` をイテレートし、順序通りに `DAGTaskNode` を作成して `graph.add_node()` する

**ステップ15** 各 `DAGTaskNode` の `task_id` は `f"{self.correlation_id}_{skill_name}"` 形式にする

**ステップ16** 各 `DAGTaskNode` の `func_name` はスキル名（`skill_name`）そのものにする

**ステップ17** 各 `DAGTaskNode` の `dependencies` は前スキルの `task_id` 単要素リストにする（最初のスキルは空リスト）

**ステップ18** `_build_dag_graph` の最後に `return graph` する

---

### Phase 2: スキル実行関数のレジストリ登録（ステップ19〜30）

**ステップ19** `Orchestrator` クラスに `_register_skills_to_scheduler()` プライベートメソッドを新規作成する

**ステップ20** `_register_skills_to_scheduler` で `if not self.dag_scheduler: return` とし、スケジューラ未設定時は即返却する

**ステップ21** `_register_skills_to_scheduler` で `self._skill_instances` をイテレートし、各スキルインスタンスの `run` メソッドを取得する

**ステップ22** 取得した `run` メソッドを `self.dag_scheduler.register_task(skill_name, run_method)` で登録する

**ステップ23** `_register_skills_to_scheduler` を `from_manifest` のインスタンス生成直後に呼び出すよう追加する

**ステップ24** `Orchestrator.run()` メソッドの先頭で `if not self.use_dag_scheduler or not self.dag_scheduler:` 条件分岐を追加する

**ステップ25** 条件が真の場合、既存の `while` ループ処理（460行目〜551行目）をそのまま実行し `return ctx` する

**ステップ26** 条件が偽の場合、`_register_skills_to_scheduler()` を呼び出す

**ステップ27** 続けて `graph = self._build_dag_graph()` で DAG を構築する

**ステップ28** `executed_graph = await self.dag_scheduler.run_dag(graph)` で DAG を実行する

**ステップ29** 実行後の `executed_graph` から最終成果物を `ctx.artifacts` にマージするロジックを書く

**ステップ30** 全ノードの `result` を走査し、辞書型なら `ctx.artifacts.update(node.result)` する

---

### Phase 3: AgentContext ↔ DAGTaskNode 変換・互換性（ステップ31〜42）

**ステップ31** `DAGTaskNode.kwargs` に `AgentContext` 相当のデータを渡せるよう、`_build_dag_graph` で `kwargs={"ctx": ctx}` を設定する

**ステップ32** スキルの `run` メソッドシグネチャが `run(ctx: AgentContext) -> AgentResult` であることを前提に、`DAGTaskNode.func` 呼び出し時に `ctx` を展開するラッパー関数を `_register_skills_to_scheduler` 内で作成する

**ステップ33** ラッパー関数内で `kwargs["ctx"]` から `AgentContext` を取り出し、スキルの `run(ctx)` を呼ぶ

**ステップ34** スキルの戻り値 `AgentResult` を `{"artifacts": result.artifacts, "next_agent": result.next_agent, "should_retry": result.should_retry, "error": result.error}` 形式の辞書に変換して返す

**ステップ35** `DAGScheduler._execute_task_wrapper` が戻り値を `graph.mark_completed(task_id, result=res)` に渡すことを確認する（既存コードで対応済み）

**ステップ36** `AgentResult.next_agent` が `AgentName` enum の場合、`.value` で文字列化して DAG 依存解決に使えるようにする

**ステップ37** `_build_dag_graph` で依存関係を構築する際、`next_agent` 情報ではなく `_ordered_skill_names` の順序のみを用いる（マニフェスト順＝実行順）

**ステップ38** `AgentResult.should_retry` が `True` の場合、DAG 側でリトライさせるため `task_node.retry_limit` を大きめ（例: 3）に設定する

**ステップ39** `AgentResult.error` がある場合、DAG 側で失敗扱いにするため `graph.mark_failed` が呼ばれるよう、ラッパーで例外を投げるか、ステータスを失敗にする

**ステップ40** ラッパー関数で `result.error` 存在時 `raise RuntimeError(result.error)` する

**ステップ41** `DAGTaskNode.timeout_seconds` をスキルごとに設定可能にするため、`_build_dag_graph` でデフォルト 300 秒を指定する

**ステップ42** `DAGTaskNode.resources` に `TaskResourceRequirement(cpu_cores=1.0, ram_mb=512)` デフォルトを指定する

---

### Phase 4: EventBus 連携・イベント発行（ステップ43〜50）

**ステップ43** `DAGScheduler` コンストラクタの `event_bus` 引数に `Orchestrator.event_bus` を渡せるよう、`from_manifest` で `dag_scheduler` 生成時に `event_bus=event_bus` を指定する

**ステップ44** `DAGScheduler` 既存の `_publish_event("dag.task_started", ...)` と `"dag.task_completed"` / `"dag.task_failed"` を確認し、Orchestrator 側のイベント発行と重複しないよう調整する

**ステップ45** `Orchestrator.run()` の DAG 実行パスでは、スキル単位の `event_bus.publish_async` を行わない（DAGScheduler 側に委譲）

**ステップ46** `Orchestrator.run()` の DAG 実行パスで、DAG 完了時に `event_bus.publish_async(AgentEvent(agent="orchestrator", payload={"status": "completed", "dag_id": graph.dag_id}, correlation_id=self.correlation_id))` を発行する

**ステップ47** DAG 失敗時（`executed_graph.has_failures()`）は `status: "failed"` で同様に発行する

**ステップ48** `DAGScheduler` の `checkpoint_interval` を 1 に設定し、各タスク完了ごとにチェックポイント保存されるよう `from_manifest` で指定する

**ステップ49** `DAGScheduler` の `persistence` に `FileSystemDAGPersistence()` を明示渡しする

**ステップ50** `DAGScheduler` の `metrics_collector` に `NoOpMetricsCollector()` を渡し、メトリクス収集を無効化する（本番では別途有効化）

---

### Phase 5: generation_tasks.py 経由の Huey タスク対応（ステップ51〜58）

**ステップ51** `src/backend/tasks/generation_tasks.py` の `_generate_orchestrated` 関数内で、`Orchestrator.from_manifest` 呼び出し時に `dag_scheduler` と `use_dag_scheduler=True` を渡す

**ステップ52** `_generate_orchestrated` で `DAGScheduler` インスタンスを生成するコードを追加する（`resource_manager`, `huey_instance`, `task_registry={}`, `use_huey=False`）

**ステップ53** 生成した `DAGScheduler` を `Orchestrator.from_manifest(..., dag_scheduler=scheduler, use_dag_scheduler=True)` に渡す

**ステップ54** `_generate_orchestrated` の最後に `scheduler.get_execution_summary(executed_graph)` を取得し、結果に `dag_summary` キーで含める

**ステップ55** `run_novel_dag_pipeline_task` との競合を避けるため、`generate_chapter_orchestrated_task` では `use_huey=False` で DAGScheduler 実行する

**ステップ56** `src/backend/routers/orchestrated.py` の `generate_orchestrated` エンドポイントが `generate_chapter_orchestrated_task` をキュー投入することを確認する（変更不要）

**ステップ57** 既存テスト `pytest tests/ -k orchestrator -v` を実行し、全パスすることを確認する

**ステップ58** 失敗するテストがあれば、該当テストファイルを開き、モックやアサーションを新インターフェースに合わせて修正する

---

### Phase 6: 動作検証・エッジケース対応（ステップ59〜68）

**ステップ59** 単体テスト用スクリプト `test_dag_integration.py` を `E:\hhh\tests/` に新規作成する

**ステップ60** テストで `Orchestrator.from_manifest(..., use_dag_scheduler=True)` を呼び、`run()` 実行後に `ctx.artifacts` に成果物が入ることを確認する

**ステップ61** テストでスキルが失敗（`error` 返却）した場合、DAG 全体が `failed` となり `cascade_cancel_downstream` が働くことを確認する

**ステップ62** テストで `should_retry=True` の場合、該当タスクがリトライされ `retry_count` が増えることを確認する

**ステップ63** テストでチェックポイントファイルが `data/dag_checkpoints/` 配下に生成されることを確認する

**ステップ64** テストで `resume_from` パラメータを使い、チェックポイントから再開できることを確認する

**ステップ65** `src/agents/orchestrator.py` の `run_ab_test` メソッドが DAGScheduler 経由でも動作するか確認し、必要なら `use_dag_scheduler=False` にフォールバックさせる

**ステップ66** `replace_skill` ホットスワップ後に `dag_scheduler.task_registry` も更新されるよう、`replace_skill` メソッド内で `self.dag_scheduler.register_task(name, new_cls().run)` を呼ぶ

**ステップ67** `set_skill_version` でバージョン切替時も同様に `task_registry` を再登録する

**ステップ68** 全テストスイート `pytest tests/ -x --tb=short` を実行し、回帰がないことを確認する

---

### Phase 7: ドキュメント・クリーンアップ（ステップ69〜72）

**ステップ69** `docs/ARCHITECTURE_PILLAR2.md` を開き、Orchestrator と DAGScheduler の統合アーキテクチャを反映させる

**ステップ70** `src/agents/orchestrator.py` のクラスdocstringに `use_dag_scheduler` パラメータの説明を追加する

**ステップ71** `git add -A && git commit -m "feat(orchestrator): integrate DAGScheduler as execution backend (Proposal 1)"` でコミットする

**ステップ72** `git push origin HEAD` でリモートにプッシュし、CI パイプラインがグリーンになることを確認する

---

## 完了判定チェックリスト

- [ ] `Orchestrator.run()` が `use_dag_scheduler=True` で DAGScheduler 経由で動作する
- [ ] 既存の `use_dag_scheduler=False`（デフォルト）で従来通りシーケンシャル実行する
- [ ] スキルの `run(ctx)` シグネチャ変更なしで動作する
- [ ] EventBus 経由のイベント発行が漏れなく行われる
- [ ] チェックポイント保存・リカバリが機能する
- [ ] 全既存テストがパスする
- [ ] 新規統合テストがパスする