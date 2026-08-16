# 提案C: ワークフロー主導パイプライン実装計画（48ステップ）

## 背景・現状

### 問題
- `PlanningAgent.rebuild_hegemony_plot()` と `PlotAgent.rebuild_plots()` に重複した再構築ロジックが存在
- 両者とも「過去文脈取得 → プロンプト構築 → LLM生成 → 監査」をほぼ同一の実装で持つ
- `PlotAgent.rebuild_hegemony_plot()` は `NotImplementedError` スタブ

### 提案Cの方针
```
PlanningAgent  = arc生成的责任のみ（generate_arcs）
PlotAgent      = plot展开のオーケストレーションのみ（expand_plots）
PlotRebuildWorkflow = その两者を组合せて再構築パイプラインを构成
```

### 新パイプライン (5ステップ)
| ステップ | 呼び出すエージェント/サービス | 责任 |
|---|---|---|
| 1 | `PlanningAgent.generate_arcs()` | start_ep以降の新arc结构を生成 |
| 2 | `PlanAuditor.audit_bible_completeness()` | 生成arcの完全性をルール検証 |
| 3 | `PlotAgent.expand_plots()` | 影响范围のepを详细展开 |
| 4 | `LogicalAuditor.audit_plot_as_issues()` | 新旧整合性をLLM検証 |
| 5 | Workflow内部 | ArcBlueprint + PlotDetail を統合して返却 |

---

## フェーズ1: 事前調査と影響範囲の确认（ステップ1〜10）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 1 | `src/agents/plot.py` | `rebuild_plots` メソッド全文を 읽고 로컬 변数を 추출（`bible_context`, `past_context`, `extra`, `prompt` 等） | 再構築ロジックの全コンポーネントが文書化されている |
| 2 | `src/agents/planning.py` | `rebuild_hegemony_plot` メソッド全文を 읽고 차이점을 분석 | PlotAgent.rebuild_plots との重複・差分をリスト化 |
| 3 | `src/backend/workflows/plot_rebuild_workflow.py` | `execute` メソッドで `plot_agent.rebuild_plots` を呼んでいる箇所を確认真 | 影响する呼出元が全て文書化されている |
| 4 | `src/core/interfaces.py` | `IPlotAgent` プロトコルの `rebuild_plots` シグネチャを確認 | 协议の完全定义が完了している |
| 5 | `src/backend/engine.py` | `UltimateHegemonyEngine` 内で `planning_agent` と `plot_agent` が 어떻게 주입되는지 확인 | DI注入パターンが文書化されている |
| 6 | `tests/unit/test_plot_agent.py` | `test_rebuild_plots_*` 测试2件の内容を確認 | 再構築相关测试が全て把握できている |
| 7 | `tests/unit/test_planning_agent.py` | `rebuild_hegemony_plot` 相关测试があるか 확인 | なければステップ36で作成 |
| 8 | `src/models/plot.py` | `ArcBlueprint` と `PlotDetail` のAttributeを確認 | 再構築结果の型が明確になっている |
| 9 | `src/agents/plan_auditor.py` | `audit_bible_completeness` の現在の引数・戻り値を确认 | ステップ2での使い方が明確 |
| 10 | `src/agents/audit.py` | `LogicalAuditor.audit_plot_as_issues` のシグネチャを確認 | ステップ4での使い方が明確 |

---

## フェーズ2: PlotRebuildWorkflow 基本构造の構築（ステップ11〜20）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 11 | `src/backend/workflows/plot_rebuild_workflow.py` | クラスdocstringを「プロット再構築专用ワークフローから、パイプライン型ワークフローへ移行」と更新 | docstringが実態と一致する |
| 12 | `src/backend/workflows/plot_rebuild_workflow.py` | `_build_rebuild_context()` を追加：作品情報・Bible・過去プロットを聚合して返すprivateメソッド | urrentとnew_total_epsを受け取りコンテキストdictを返す |
| 13 | `src/backend/workflows/plot_rebuild_workflow.py` | `_validate_inputs(params)` を追加：必須パラメータの存在・ 범위妥当性を検証 | 不到なパラメータ時にValueErrorを発生させる |
| 14 | `src/backend/workflows/plot_rebuild_workflow.py` | `_assemble_result(new_arcs, expanded_plots)` を追加：ArcBlueprintリストとPlotDetailリストを 결과dictに統合 | `{"arcs": [...], "expanded": [...], "count": N}` を返す |
| 15 | `src/backend/workflows/plot_rebuild_workflow.py` | `_handle_error(step_name, exception)` を追加：各ステップ失敗時のエラー処理を统一 | ロガー出力＋reporter報告＋例外を再スロー |
| 16 | `src/backend/workflows/plot_rebuild_workflow.py` | `execute` メソッドの先頭に `_validate_inputs(params)` を挿入 | バリデーションがパイプライン前に実行される |
| 17 | `src/backend/workflows/plot_rebuild_workflow.py` | `execute` メソッドの try/except 構造を追加（ステップ18-27を wrap） | 例外時の適切な処理が确保されている |
| 18 | `src/backend/workflows/plot_rebuild_workflow.py` | reporter 引数に default None を追加（null安全） | reporter省略時{\"done\": False, \"error\": ...}を返す |
| 19 | `src/backend/workflows/plot_rebuild_workflow.py` | パイプライン结果のログ出力を追加（logger.info） | 成功・失敗いずれの場合もログに記録される |
| 20 | `tests/unit/test_workflows.py`（新規） | `_TestPlotRebuildWorkflowBuilder` ヘルパを作成し、mock engineを作成する | テストでワークフローがインスタンス化できる |

---

## フェーズ3: パイプライン本体1 — ステップ1（新規arc生成）（ステップ21〜25）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 21 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step1_generate_new_arcs(context, params)` を実装 | `PlanningAgent.generate_arcs()` を呼び、ArcListを返す |
| 22 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step1_generate_new_arcs` 内で `build_arc_generation_prompt` に渡す引数を工夫：start_ep=params["start_ep"]、new_total_eps=params["new_total"]、keywords=params["new_keywords"] | target_eps 以降 частьのみ生成される |
| 23 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step1_generate_new_arcs` 内で Bible コンテキストを正しく构建：`bible = await self.engine.repo.get_latest_bible(context["book_id"])`、then pass to generate_arcs as `bible=bible` | Bible情報がLLMプロンプトに反映される |
| 24 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step1_generate_new_arcs` 内で trend_memo + past_context を keywords/synopsis に 병합 | 过去プロットとの連続性が確保される |
| 25 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step1_generate_new_arcs` 失敗時に `_handle_error("step1_arc_generation", e)` を呼ぶ | ステップ1の失敗が適切に處理される |

---

## フェーズ4: パイプライン本体2 — ステップ2（arc監査）（ステップ26〜28）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 26 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step2_audit_arcs(new_arcs, reporter)` を実装 | `PlanAuditor.audit_bible_completeness()` を呼び、is_consistentがFalseなら警告を報告 |
| 27 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step2_audit_arcs` 内で new_arcs を dict-like bible オブジェクトに変換（`{"arcs": [a.model_dump() for a in new_arcs.arcs]}` 等） | PlanAuditorが 요구する形式に맞춤 |
| 28 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step2_audit_arcs` 内で issues が空でない場合 `reporter.report("⚠️ ステップ2監査課題: " + "; ".join(issues), "warning")` を呼ぶ | 警告がユーザー通知される |

---

## フェーズ5: パイプライン本体3 — ステップ3（plot展開）（ステップ29〜33）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 29 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step3_expand_affected_eps(context, new_arcs, params)` を実装 | `PlotAgent.expand_plots()` を呼び、PlotDetailリストを返す |
| 30 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step3_expand_affected_eps` 内で対象話数を计算：`ep_nums = list(range(params["start_ep"], params["new_total"] + 1))` | new_total まで全話が対象 |
| 31 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step3_expand_affected_eps` 内で arcs を抽出：`arc_list = new_arcs.arcs`（ArcList の arcs 属性） | IPlotExpander に Arcリストが渡る |
| 32 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step3_expand_affected_eps` 内で `branch_id` を正しく抽出：`book.current_branch_id or 1` | 分岐対応が维持される |
| 33 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step3_expand_affected_eps` 内で reporter を传递し、force=True で既存plotを上書き | 再構築时的强制上書きが動作する |

---

## フェーズ6: パイプライン本体4 — ステップ4（整合性監査）（ステップ34〜37）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 34 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step4_audit_expanded(new_arcs, expanded_plots, context, params)` を実装 | `LogicalAuditor.audit_plot_as_issues()` を呼び、各arcの整合性を検証 |
| 35 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step4_audit_expanded` 内でループ：`for arc in new_arcs.arcs: issues = await auditor.audit_plot_as_issues(book_id, branch_id, arc.end_ep, arc.summary)` | 各アークの終了話で監査が実行される |
| 36 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step4_audit_expanded` 内で `not issues.is_consistent` の場合に `reporter.report(f"⚠️ 第{arc.arc_num}アーク監査課題: {issues}", "warning")` | 課題が通知される |
| 37 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step4_audit_expanded` 内で監査例外をキャッチ：`except Exception as e: logger.warning("ステップ4監査スキップ: %s", e)` | 監査失敗でもパイプラインが停止しない |

---

## フェーズ7: パイプライン本体5 — ステップ5（結果統合）（ステップ38〜40）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 38 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step5_assemble_result(new_arcs, expanded_plots)` を実装 | `{"arcs": [a.model_dump() for a in new_arcs.arcs], "expanded": [p.model_dump() for p in expanded_plots], "count": len(expanded_plots)}` を返す |
| 39 | `src/backend/workflows/plot_rebuild_workflow.py` | `_step5_assemble_result` 内にnull checks：`if expanded_plots is None: expanded = []` | 空リスト対応 |
| 40 | `src/backend/workflows/plot_rebuild_workflow.py` | execute() の戻り値を `{"done": True, "arcs": arcs, "expanded": expanded, "count": count}` に统一 | 既存の `{"done": True, "count": len(results)}` から拡張 |

---

## フェーズ8: execute() パイプライン orchestrator の完成（ステップ41〜43）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 41 | `src/backend/workflows/plot_rebuild_workflow.py` | execute() 内で以下を顺序実行：1) context = _build_rebuild_context()、2) new_arcs = _step1_generate_new_arcs()、3) _step2_audit_arcs()、4) expanded = _step3_expand_affected_eps()、5) _step4_audit_expanded()、6) return _step5_assemble_result() | 5ステップが顺序実行される |
| 42 | `src/backend/workflows/plot_rebuild_workflow.py` | execute() 内にパイプライン進捗の reporter 報告を追加：「プロット再構築パイプライン開始」→各ステップ開始時→完了時 | 進捗がユーザーに伝わる |
| 43 | `src/backend/workflows/plot_rebuild_workflow.py` | execute() の戻り値に `_build_rebuild_context()` で算出した metadata（book_title、start_ep、new_total等）を追加 | り返り値に 풍부な情報が含まれる |

---

## フェーズ9: IPlotAgent プロトコル更新 — rebuild_plots の 제거（ステップ44〜45）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 44 | `src/core/interfaces.py` | `IPlotAgent` プロトコルから `rebuild_plots` メソッドを削除し、docstringを「Plot展開のみを担当」に更新 | プロトコルが expand_plots のみを要求する |
| 45 | `src/core/interfaces.py` | 新規 `@runtime_checkable class IPlotExpander(Protocol):` を追加し `expand_plots` シグネチャを移動 | 構造的型付けが维持される |

---

## フェーズ10: PlotAgent から rebuild_plots を削除（ステップ46〜47）

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 46 | `src/agents/plot.py` | `rebuild_plots` メソッドを完全削除 | PlotAgent に再構築メソッドがなくなる |
| 47 | `src/agents/plot.py` | クラスdocstringを「プロット展開のオーケストレーションを担当」に更新 | docstring が责務と一致する |
| 48 | `src/agents/plot.py` | `rebuild_hegemony_plot` スタブ（NotImplementedError）も削除 | 未実装スタブがなくなる |

---

## 残余ステップ（49〜54）：PlanningAgent から rebuild_hegemony_plot を削除 + テスト

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 49 | `src/agents/planning.py` | `rebuild_hegemony_plot` メソッドを完全削除 | PlanningAgent に再構築メソッドがなくなる |
| 50 | `src/agents/planning.py` | クラスdocstringを「企画・アーク立案を担当」に更新 | docstring が责務と一致する |
| 51 | `tests/unit/test_workflows.py` | `test_plot_rebuild_workflow_pipeline_success` を追加：mock agents + execute → `done=True` + `count > 0` | 正常系テストが通過する |
| 52 | `tests/unit/test_workflows.py` | `test_plot_rebuild_workflow_arc_generation_failure` を追加：step1 例外時 → `done=False` + error | 異常系テストが通过する |
| 53 | `tests/unit/test_workflows.py` | `test_plot_rebuild_workflow_expansion_failure_degrades` を追加：step3 例外時 → 空expandedを返して成功継続 | 異常系テストが通过する |
| 54 | `ruff check src/agents/plot.py src/agents/planning.py src/backend/workflows/plot_rebuild_workflow.py` | 全ファイル lint error 0 | lint グリーン |

---

## 残余ステップ（55〜59）：API / 呼出元の更新

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 55 | `src/backend/server.py` | `rebuild_plots` エンドポイントが `plot_agent.rebuild_plots` を呼んでいる箇所을 `workflow.execute()` に変更 | API が新規ワークフローを使用 |
| 56 | `src/core/null_objects.py` | `NullPlotIntegrityMonitor` に `expand_plots` がなきか確認（なければ追加） | 構造的型付けが維持 |
| 57 | `src/backend/engine.py` | `UltimateHegemonyEngine` 内で `plot_agent` の型注釈を更新（`IPlotExpander` への適合を確認） | 型安全が維持 |
| 58 | `src/agents/__init__.py` | `PlotAgent` エクスポートの docstring を「expand_plots 担当」に更新 | ドキュメント整合性 |
| 59 | `pytest tests/unit/test_plot_agent.py tests/unit/test_planning_agent.py tests/unit/test_workflows.py` | 全テスト green | テストスイート全面green |

---

## 残余ステップ（60〜66）：最终検証・クリーンアップ

| # | ファイル | アクション（原子的） | 受入基準 |
|---|---|---|---|
| 60 | `docs/agent_interaction.md` | エージェント相互作用図を更新：PlotAgent → PlanningAgent の破線（再構築）を削除し、PlotRebuildWorkflow を新しいオーケストレーターとして追加 | 図が実際の構成と一致 |
| 61 | `docs/adr/0002-ai-orchestration-framework.md` | ADR-0002 に Proposal C の решение を記述：ワークフロー主導パイプラインへ移行 | アーキテクチャ决定が文書化 |
| 62 | `plans/plot_agent_improvements_72steps.md` | このファイルの内容を「72steps → 48steps + Proposal C 採用」に更新し、古い提案をアーカイブ | 計画文档が最新 |
| 63 | `src/backend/workflows/plot_rebuild_workflow.py` | execute() に充分的 docstring を追加（各ステップの目的、戻り値、パイプライン图） | コードドキュメントが整備 |
| 64 | `ruff check src/agents/plot.py src/agents/planning.py src/backend/workflows/plot_rebuild_workflow.py` | 再度全ファイル lint error 0 | lint 維持 |
| 65 | `mypy --config-file pyproject.toml src/agents/plot.py src/agents/planning.py src/backend/workflows/plot_rebuild_workflow.py` | 型検査 error 0 | 型安全維持 |
| 66 | `pytest tests/ -q` | 全テスト green（rebuild相关テストは test_workflows.py のみ） | 完全テスト通過 |

---

## 実装顺序の注意事项

1. **フェーズ1〜2を最初に行う**：現在の重複ロジックを完全に理解してから実装を開始すること
2. **フェーズ9（IPlotAgent 更新）をフェーズ10より先に行う**： PlotAgentのrebuild削除前にプロトコルを更新しないと、静的型チェックでエラーが発生する
3. **フェーズ3〜4（ステップ21〜28）を连续して実装**：ステップ1と2は密な依赖関係がある
4. **ステップ55（API更新）は最后に近い段階**：API client 更新を早期に行うとテストが困難になる
5. **ステップ60〜62（ドキュメント更新）はステップ54以降**：実際の動作确認後にドキュメントを更新する

---

## リスクと回避策

| リスク | 回避策 |
|---|---|
| `IPlotAgent` から `rebuild_plots` を削除すると、静的チェックで大规模なコンパイルエラーが発生 | ステップ44-45をフェーズ10より先に実行し、徐々に対応 |
| パイプライン内のエラー処理が不完全で、某个ステップ失敗時にパイプラインが停止する | ステップ17の try/except 構造で全てを包み、ステップ38で部分結果を返す |
| 新規 `_build_rebuild_context` が `book.current_branch_id` を正しく取得できず、branch 分離が崩壊する | ステップ12で `repo.get_book()` → `book.current_branch_id` の널 安全処理を徹底 |
| `PlanningAgent.generate_arcs` が部分的なarc生成（start_ep以降のみ）に対応していない | ステップ22の引数調整で確認要做。必要なら `generate_arcs` を 수정（後述） |
| `generate_arcs` の `target_eps` が「新话说数」而非「全话说数」の場合、arc生成が不正确 | `target_eps = params["new_total"] - params["start_ep"] + 1` を明示的に計算 |

---

## `PlanningAgent.generate_arcs` の部分arc生成への対応（必要に応じて）

現在の `generate_arcs` は「1話からtarget_eps话までの全arcを生成」する設計。再構築では「start_ep话から最终话までのarcのみ」を生成する必要がある場合、以下の対応を行う：

| # | ファイル | アクション | 受入基準 |
|---|---|---|---|
| A1 | `src/agents/planning.py` | `generate_arcs` に `start_ep: int = 1` 引数を追加し、`build_arc_generation_prompt` に 전달 | start_ep以降のみでarcが生成される |
| A2 | `src/agents/planning.py` | `generate_arcs` 内で `target_eps` を `target_eps - start_ep + 1` に调整してプロンプトに渡す | 生成されるarcが指定话数以内に抑えられる |
| A3 | `src/agents/planning.py` | `_fallback_arcs` も同じ調整を行う | フォール백時も整合性が维持される |
| A4 | `tests/unit/test_planning_agent.py` | `start_ep` 引数のテストを追加 | 部分生成が検証される |

**Note**: A1〜A4 は実際には不要かもしれない。`target_eps = 50`、`start_ep = 30` の場合、LLMは「30-50话のarc」を生成するプロンプトを构建できる。ステップ22で `start_ep` を `synopsis` に加える（例：「第30话からの物語構成：...」） 방법으로解决可能的。