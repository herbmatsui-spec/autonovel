# Orchestrator 一本化 実装計画書（72ステップ）

## 前提
- 対象リポジトリ: `E:\hhh`
- 設計仕様: `docs/architecture.md` の Orchestrator + 8エージェント構成
- 目標: 4重エンジンを Orchestrator 単一アーキテクチャに統合

---

### Phase 0: 準備・環境確認（ステップ 1-4）

1. `src/legacy/` ディレクトリを作成する
2. `git status` を実行し、現在の変更状況を記録する
3. `python -m pytest tests/integration/test_full_pipeline.py -v --collect-only` を実行し、既存テストのベースラインを確認する
4. `grep -r "UltimateHegemonyEngine" --include="*.py" src/` を実行し、参照箇所を全洗い出しして `legacy_refs.txt` に保存する

### Phase 1: レガシーエンジンのアーカイブ（ステップ 5-12）

5. `src/backend/engine.py` を `src/legacy/engine_ultimate_hegemony.py` へ移動する
6. `src/services/novel_producer.py` を `src/legacy/novel_producer.py` へ移動する
7. `src/agents/writing/_writing.py` を `src/legacy/writing_agent_v1.py` へ移動する
8. `src/legacy/__init__.py` を作成し、空ファイルとする
9. `src/backend/engine.py` を新規作成し、以下の内容のみ記述する：
   ```python
   """Legacy UltimateHegemonyEngine は削除されました。Orchestrator を使用してください。"""
   raise ImportError("UltimateHegemonyEngine is removed. Use src.agents.orchestrator.Orchestrator instead.")
   ```
10. `src/services/novel_producer.py` を新規作成し、以下の内容のみ記述する：
    ```python
    """Legacy NovelProducer は削除されました。Orchestrator を使用してください。"""
    raise ImportError("NovelProducer is removed. Use src.agents.orchestrator.Orchestrator instead.")
    ```
11. `src/agents/writing/_writing.py` を新規作成し、以下の内容のみ記述する：
    ```python
    """Legacy WritingAgent (_writing.py) は削除されました。src.agents.writing.agent.WritingAgent を使用してください。"""
    raise ImportError("Legacy WritingAgent removed. Use src.agents.writing.agent.WritingAgent instead.")
    ```
12. `python -m pytest tests/ -x --tb=short 2>&1 | head -100` を実行し、ImportError の発生箇所を特定する

### Phase 2: Import 参照の一括書き換え（ステップ 13-24）

13. `legacy_refs.txt` を読み、各ファイルの `from src.backend.engine import UltimateHegemonyEngine` を `from src.agents.orchestrator import Orchestrator` に置換する
14. `legacy_refs.txt` を読み、各ファイルの `from src.services.novel_producer import NovelProducer` を `from src.agents.orchestrator import Orchestrator` に置換する
15. `legacy_refs.txt` を読み、各ファイルの `from src.agents.writing._writing import WritingAgent` を `from src.agents.writing.agent import WritingAgent` に置換する
16. `grep -r "UltimateHegemonyEngine" --include="*.py" src/` を実行し、残存参照がゼロであることを確認する
17. `grep -r "NovelProducer" --include="*.py" src/` を実行し、残存参照がゼロであることを確認する
18. `grep -r "_writing" --include="*.py" src/agents/writing/` を実行し、残存参照がゼロであることを確認する
19. `src/backend/routers/books.py` を開き、エンジン初期化箇所を `Orchestrator.from_manifest(...)` に書き換える
20. `src/backend/workflows/easy_mode_workflow.py` を開き、エンジン呼び出しを `Orchestrator` 経由に書き換える
21. `src/backend/workflows/full_auto_workflow.py` を開き、エンジン呼び出しを `Orchestrator` 経由に書き換える
22. `src/backend/tasks/generation_tasks.py` を開き、インポートと実行パスを `Orchestrator` に書き換える
23. `src/backend/writing_service.py` を開き、`UltimateHegemonyEngine` 参照を `Orchestrator` に書き換える
24. `python -m pytest tests/integration/test_orchestrated_api.py -v` を実行し、API テストが通ることを確認する

### Phase 3: WritingAgent 単一化（ステップ 25-34）

25. `src/agents/writing/agent.py` を開き、クラス定義が `SkillAgent` 継承であることを確認する
26. `src/agents/writing/writing.py` を開き、全メソッドを削除し、以下のみを残す：
    ```python
    from .agent import WritingAgent
    __all__ = ["WritingAgent"]
    ```
27. `src/agents/writing/__init__.py` を開き、`from .agent import WritingAgent` のみを export する
28. `src/agents/writing/generator.py` を開き、`WritingGenerator` クラスが独立して利用可能であることを確認する
29. `src/agents/writing/episode_writer.py` を開き、`EpisodeWriter` クラスが `WritingGenerator` を使用していることを確認する
30. `src/agents/writing/rewrite_orchestrator.py` を開き、`RewriteOrchestrator` が `WritingAgent` (agent.py版) を受け取ることを確認する
31. `src/agents/writing/bible_extractor.py` を開き、依存関係を確認する
32. `python -m pytest tests/integration/test_full_pipeline.py -v -k "writing" 2>&1 | head -50` を実行し、Writing 関連テストが通ることを確認する
33. `grep -r "from src.agents.writing import" --include="*.py" src/` を実行し、全て `agent` 経由になっていることを確認する
34. `grep -r "WritingAgent" --include="*.py" src/agents/writing/` を実行し、重複定義がないことを確認する

### Phase 4: easy_mode を Orchestrator マニフェスト化（ステップ 35-46）

35. `src/agents/skills/v1/` 配下に `easy_mode_planning.py` を作成し、`PlanningSkill` クラスを実装する
36. `src/agents/skills/v1/` 配下に `easy_mode_plot.py` を作成し、`PlotSkill` クラスを実装する
37. `src/agents/skills/v1/` 配下に `easy_mode_bible.py` を作成し、`BibleSkill` クラスを実装する
38. `src/agents/skills/v1/` 配下に `easy_mode_context_builder.py` を作成し、`ContextBuilderSkill` クラスを実装する
39. `src/agents/skills/v1/` 配下に `easy_mode_writing.py` を作成し、`WritingSkill` クラスを実装する（`WritingAgent` を内部使用）
40. `src/agents/skills/v1/` 配下に `easy_mode_illustration.py` を作成し、`IllustrationSkill` クラスを実装する（簡易版）
41. `src/agents/skills/v1/` 配下に `easy_mode_marketing.py` を作成し、`MarketingSkill` クラスを実装する（簡易版）
42. `src/agents/skills/v1/__init__.py` に全スキルを追加する
43. `config/manifests/easy_mode.yaml` を新規作成し、以下の構成で記述する：
    ```yaml
    skills:
      - name: "easy_mode_planning"
        depends_on: []
        runs_after: []
        config: {enabled: true}
      - name: "easy_mode_plot"
        depends_on: ["easy_mode_planning"]
        config: {enabled: true}
      - name: "easy_mode_bible"
        depends_on: ["easy_mode_planning"]
        config: {enabled: true}
      - name: "easy_mode_context_builder"
        depends_on: ["easy_mode_plot", "easy_mode_bible"]
        config: {enabled: true}
      - name: "easy_mode_writing"
        depends_on: ["easy_mode_context_builder"]
        config: {enabled: true}
      - name: "easy_mode_illustration"
        depends_on: ["easy_mode_writing"]
        config: {enabled: true}
      - name: "easy_mode_marketing"
        depends_on: ["easy_mode_writing"]
        config: {enabled: true}
    ```
44. `src/backend/routers/easy_mode.py` を開き、`generate_with_llm` 関数を削除する
45. `src/backend/routers/easy_mode.py` に `POST /easy_mode/generate` エンドポイントを追加し、内部で `Orchestrator.from_manifest("config/manifests/easy_mode.yaml")` を呼び出す実装に置き換える
46. `src/backend/routers/easy_mode.py` の `export_easy_mode_package` エンドポイントを `Orchestrator` 経由の成果物取得に書き換える

### Phase 5: DI コンテナ統一（ステップ 47-54）

47. `src/config/container.py` を開き、`UltimateHegemonyEngine` の登録を削除する
48. `src/config/container.py` に `Orchestrator` のシングルトン登録を追加する
49. `src/config/container.py` に `WritingAgent` (agent.py版) のシングルトン登録を追加する
49. `src/config/container.py` に `EventBus` (インメモリ) の登録を追加する
50. `src/backend/server.py` の `app.include_router` 周辺で、起動時のコンテナ初期化を確認する
51. `src/backend/routers/orchestrated.py` が存在することを確認し、DI 経由で `Orchestrator` を取得していることを確認する
52. `src/backend/workflows/__init__.py` のワークフロー登録で、コンテナから `Orchestrator` を取得するように修正する
53. `python -c "from src.config.container import container; print(container.orchestrator)"` を実行し、DI 解決が成功することを確認する
54. `python -c "from src.config.container import container; print(container.writing_agent)"` を実行し、DI 解決が成功することを確認する

### Phase 6: 設定・環境変数の整理（ステップ 55-60）

55. `config/settings.py` を開き、`USE_REDIS_EVENTS` 以外のレガシー設定項目を削除する
56. `config/settings.py` に `DEFAULT_ORCHESTRATOR_MANIFEST = "config/manifests/orchestrated.yaml"` を追加する
57. `config/settings.py` に `EASY_MODE_MANIFEST = "config/manifests/easy_mode.yaml"` を追加する
58. `config/manifests/orchestrated.yaml` を作成し、8エージェント全フローのマニフェストを記述する
59. `.env.example` に `USE_REDIS_EVENTS=false` とマニフェストパスを追加する
60. `python -m pytest tests/integration/test_orchestrated_api.py tests/integration/test_full_pipeline.py -v` を実行し、全統合テストが通ることを確認する

### Phase 7: テスト・検証・クリーンアップ（ステップ 61-72）

61. `python -m pytest tests/unit/ -v --tb=short 2>&1 | tail -30` を実行し、単体テスト全通過を確認する
62. `python -m pytest tests/integration/ -v --tb=short 2>&1 | tail -50` を実行し、統合テスト全通過を確認する
63. `curl -X POST http://localhost:8000/orchestrated/generate -H "Content-Type: application/json" -d '{"title":"Test","synopsis":"Test","target_eps":1}'` を実行し、Orchestrator エンドポイントが動作することを確認する
64. `curl -X POST http://localhost:8000/easy_mode/generate -H "Content-Type: application/json" -d '{"title":"Test","synopsis":"Test","target_eps":1}'` を実行し、easy_mode エンドポイントが動作することを確認する
65. `grep -r "UltimateHegemonyEngine\|NovelProducer\|_writing" --include="*.py" src/ | grep -v "legacy" | grep -v "test" | grep -v ".pyc"` を実行し、残存参照がゼロであることを確認する
66. `find src/legacy -name "*.py" | xargs wc -l` を実行し、アーカイブされたファイルサイズを記録する
67. `git diff --stat` を実行し、変更行数を確認する
68. `git add -A && git commit -m "refactor: unify generation engines under Orchestrator (Proposal 1)"` を実行する
69. `python -m pytest tests/integration/test_easy_mode_export.py -v` を実行し、easy_mode 書き出しテストが通ることを確認する
70. `python -m pytest tests/integration/test_generate_flow.py -v` を実行し、生成フロー全テストが通ることを確認する
71. `README.md` のアーキテクチャ図・説明を Orchestrator 単一構成に更新する
72. `docs/architecture.md` の「現状・乖離点」セクションを削除し、「実装済み: Orchestrator 単一アーキテクチャ」と記述する