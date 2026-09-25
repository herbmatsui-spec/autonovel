# PLAN: 感情状態キャッシュ Week 5 - 階層的エージェントメモリ (MemGPT流自律管理)
**目標**: 執筆エージェントに Core/Working/Archival 3層メモリを持たせ、感情状態を自律更新・検索・圧縮させる
**前提**: Week 1-4 のストア層 (Vector/Graph/Log) が Archival Memory のバックエンドとして完成済み

---

## Step 1-24 実装タスク

### Phase 1: メモリアーキテクチャ基盤 (Steps 1-6)

**Step 1: メモリインターフェース定義**
- ファイル: `src/agent/memory/interfaces.py` (新規)
- クラス (ABC):
  - `MemoryBlock` (基底): `read() -> str`, `write(content: str)`, `size() -> int`
  - `CoreMemory` (常駐): `get(key) -> Any`, `set(key, value)`, `dump() -> Dict`
  - `ArchivalMemory` (外部): `search(query: str, k: int) -> List[MemoryEntry]`, `insert(entry: MemoryEntry)`, `delete(id: str)`
  - `WorkingMemory` (揮発): `push(frame: WorkingFrame)`, `pop() -> WorkingFrame`, `peek() -> WorkingFrame`
- `MemoryEntry`: `id, content, embedding, metadata, timestamp`
- `WorkingFrame`: `scene_id, emotional_beats, plot_points, context_summary`
- テスト: `tests/unit/agent/memory/test_interfaces.py::test_core_memory_crud`

**Step 2: CoreMemory 実装 (インメモリ・永続化対応)**
- ファイル: `src/agent/memory/core_memory.py` (新規)
- クラス: `CoreMemory`
- 内部構造:
  ```python
  {
    "character_emotions": {  # ペアごと感情ベクトル (Week 4 FusedVector ミラー)
      "A->B": {"affection": 0.3, "tension": 0.8, "fear": 0.6, "cause": "ep14_betrayal", "updated": "ep14_end"}
    },
    "relationship_dynamics": {  # 関係性メタ情報
      "A-B": {"trust_trajectory": [-0.1, -0.3, 0.2], "major_events": ["ep14_betrayal", "ep16_rescue"]}
    },
    "active_hooks": ["resolve_A_B_tension", "reveal_B_secret"],  # 今話で解決すべき感情フック
    "writing_style_notes": "Aは内心を顔に出さない"
  }
  ```
- 永続化: `save_to_disk(path)`, `load_from_disk(path)` (JSON)
- トークン予算管理: `estimate_tokens() -> int`, `compact_if_needed(max_tokens: int)`
- テスト: `tests/unit/agent/memory/test_core_memory.py::test_token_budget_compaction`

**Step 3: ArchivalMemory アダプター (Week 1-4 ストア統合)**
- ファイル: `src/agent/memory/archival_memory.py` (新規)
- クラス: `ArchivalMemory`
- 依存: `VectorStore`, `GraphStore`, `EventLogStore`, `EmbeddingModel` (軽量: sentence-transformers/all-MiniLM-L6-v2)
- メソッド:
  - `search_emotional_scenes(query: str, k: int=5) -> List[MemoryEntry]`: VectorStore 類似検索
  - `trace_emotional_cause(source, target, emotion) -> List[Dict]`: GraphStore 因果パス探索
  - `get_emotional_history(pair, from_ep, to_ep) -> List[Dict]`: EventLogStore 再生
  - `insert_emotional_summary(episode: int, summary: str, vector: EmotionalVector)`: 要約保存
- 埋め込み: `EmbeddingModel` はシングルトンで起動時ロード (CPU推論 ~50ms)
- テスト: `tests/integration/agent/memory/test_archival_adapter.py::test_search_scenes`

**Step 4: WorkingMemory 実装 (シーン単位フレーム)**
- ファイル: `src/agent/memory/working_memory.py` (新規)
- クラス: `WorkingMemory`
- 最大フレーム数: 3-5 (直近シーンのみ)
- フレーム内容: 現在シーンの感情ビート、プロット進行、コンテキスト要約
- 自動要約: フレーム溢れ時、古いフレームを `ArchivalMemory.insert_emotional_summary()` へ退避
- テスト: `tests/unit/agent/memory/test_working_memory.py::test_frame_eviction_to_archival`

**Step 5: メモリマネージャー (3層統合)**
- ファイル: `src/agent/memory/manager.py` (新規)
- クラス: `MemoryManager`
- 役割: Core/Working/Archival の統合インターフェース
- メソッド:
  - `get_emotional_context(pair) -> Dict`: Core → なければ Archival 検索
  - `update_emotion(source, target, emotion, delta, reason)`: Core 更新 + Archival 同期 (非同期)
  - `recall_similar(query, k) -> List`: Archival 検索
  - `trace_cause(source, target, emotion) -> List`: Archival Graph 探索
  - `compact()`: Core 圧縮 → 古い情報を Archival へ
- テスト: `tests/unit/agent/memory/test_manager.py::test_get_emotional_context_fallback`

**Step 6: エージェント用ツール定義 (Function Calling)**
- ファイル: `src/agent/tools/memory_tools.py` (新規)
- ツール群 (OpenAI Function Calling / Anthropic Tools 形式):
  ```python
  tools = [
    {"name": "update_emotion", "description": "感情値更新", "parameters": {"source","target","emotion","delta","reason"}},
    {"name": "get_emotional_context", "description": "ペアの感情状態取得", "parameters": {"source","target"}},
    {"name": "recall_similar_scene", "description": "類似感情シーン検索", "parameters": {"query","k"}},
    {"name": "trace_emotional_cause", "description": "感情の因果パス探索", "parameters": {"source","target","emotion"}},
    {"name": "add_relationship_note", "description": "関係性メモ追加", "parameters": {"pair","note"}},
    {"name": "compact_core_memory", "description": "CoreMemory圧縮実行", "parameters": {}},
    {"name": "set_active_hook", "description": "今話解決フック設定", "parameters": {"hook"}},
  ]
  ```
- 実装: 各ツール → `MemoryManager` メソッド呼び出しラッパー
- テスト: `tests/unit/agent/tools/test_memory_tools.py::test_update_emotion_tool`

---

### Phase 2: Writer Agent 統合 (Steps 7-14)

**Step 7: Writer Agent ベースクラス拡張**
- ファイル: `src/agents/writer_agent.py` (既存編集)
- 追加属性: `memory_manager: MemoryManager`, `tools: List[Tool]`
- `__init__` で `MemoryManager` 初期化 (CoreMemory ディスクから復元 or 新規)
- システムプロンプトにメモリ操作指示追加:
  ```
  あなたは感情メモリを持つ小説執筆エージェントです。
  CoreMemory に主要キャラの感情状態が常駐しています。
  執筆中に感情変化を検知したら update_emotion ツールを呼び出してください。
  過去シーンを参照したい場合は recall_similar_scene を使用してください。
  ```
- テスト: `tests/unit/agents/test_writer_agent_memory.py::test_agent_has_memory_manager`

**Step 8: 執筆ループへのメモリ統合**
- ファイル: `src/agents/writer_agent.py` (追加)
- メソッド: `write_episode(episode: int, plot_outline: str) -> str`
- フロー:
  1. `memory_manager.core_memory.load()` (前回保存分復元)
  2. `memory_manager.core_memory` 内容をシステムプロンプトに注入 (JSON整形)
  3. LLM 呼び出し (tools 有効化)
  4. ツール呼び出し検知 → `memory_manager` 経由で実行 → 結果を LLM に返却
  5. 生成完了 → `memory_manager.core_memory.save()` (ディスク永続化)
  6. `WorkingMemory` クリア
- テスト: `tests/integration/agents/test_writer_memory_loop.py::test_write_episode_updates_core_memory`

**Step 9: 感情変化検知プロンプトエンジニアリング**
- ファイル: `src/agents/prompts/emotion_detection.md` (新規、プロンプトテンプレート)
- 指示例:
  ```
  ## 感情変化検知ルール
  以下のパターンを検知したら update_emotion を呼び出せ：
  - キャラが発言・行動で明確な感情表明をした
  - 内心描写で感情変化が示された
  - 他キャラへの態度変化があった
  - 重要なプロットイベント (裏切り・救出・告白等) が発生した
  
  delta 目安: 軽微=±0.1, 中程度=±0.3, 大きい=±0.5 以上
  原因は具体的に (例: "AがBの裏切りを目撃")。
  ```
- システムプロンプトに埋め込み
- テスト: `tests/unit/agents/test_emotion_detection_prompt.py::test_prompt_contains_rules`

**Step 10: ツール実行ハンドラー・エラーハンドリング**
- ファイル: `src/agents/tool_handler.py` (新規)
- クラス: `ToolHandler`
- 役割: LLM からのツール呼び出し → 実装関数マッピング → 実行 → 結果整形 → LLM 返却
- エラー処理: 例外キャッチ → エラー内容を LLM に返却 (再試行促す)
- タイムアウト: ツール実行 30秒
- 並列実行: 独立ツール呼び出しは `asyncio.gather`
- テスト: `tests/unit/agents/test_tool_handler.py::test_tool_error_handling`

**Step 11: CoreMemory 圧縮ポリシー実装**
- ファイル: `src/agent/memory/compaction.py` (新規)
- クラス: `CompactionPolicy`
- 戦略:
  1. `character_emotions`: 更新古い順 (5話以上前) → 要約生成 → Archival へ移動、Core から削除
  2. `relationship_dynamics`: `trust_trajectory` は直近10話のみ保持、古いのは統計値 (平均・傾向) に圧縮
  3. `active_hooks`: 解決済みフック削除、未解決のみ保持
  4. `writing_style_notes`: 変更なければ保持
- 実行トリガー: `core_memory.estimate_tokens() > MAX_TOKENS (デフォルト 2000)`
- テスト: `tests/unit/agent/memory/test_compaction.py::test_compact_old_emotions`

**Step 12: エピソード境界での自動圧縮・保存**
- ファイル: `src/agents/writer_agent.py` (追加)
- `write_episode` 終了時:
  1. `memory_manager.compact()` 実行
  2. `memory_manager.core_memory.save_to_disk(episode_path)`
  3. `memory_manager.archival.insert_emotional_summary(episode, summary, fused_vector)` (Week 4 融合ベクトル使用)
- 要約生成: LLM に「この話の感情的ハイライトを3文で」プロンプト → 1回呼び出し
- テスト: `tests/integration/agents/test_episode_boundary.py::test_auto_compact_and_save`

**Step 13: メモリ初期化・リセット機能**
- ファイル: `src/agent/memory/initializer.py` (新規)
- 関数: `initialize_memory_for_project(project_id: str) -> MemoryManager`
- 新規プロジェクト: 空 CoreMemory 作成
- 既存プロジェクト: 最新エピソードの CoreMemory ロード
- 分岐対応: ブランチごとに CoreMemory 別管理 (ディレクトリ分離)
- CLI: `python -m src.agent.memory.initializer init --project my_novel --branch main`
- テスト: `tests/unit/agent/memory/test_initializer.py::test_init_new_project`

**Step 14: Agent 統合テスト (E2E)**
- ファイル: `tests/integration/agents/test_writer_agent_e2e.py` (新規)
- シナリオ:
  1. 新規プロジェクトで Agent 起動
  2. 第1話執筆 → CoreMemory に感情状態蓄積確認
  3. 第2話執筆 → 第1話の感情がプロンプトに注入されること確認
  4. `update_emotion` ツール自動呼び出し確認
  5. 圧縮トリガー (トークン超過シミュレーション) → Archival へ退避確認
  6. プロジェクト再起動 → CoreMemory 復元確認

---

### Phase 3: 高度機能・最適化 (Steps 15-20)

**Step 15: 感情的整合性チェックツール**
- ファイル: `src/agent/tools/consistency_tool.py` (新規)
- ツール: `check_emotional_consistency`
- 機能: 現在 CoreMemory 状態 vs 直前話の融合ベクトル (Week 4) 比較
- 検出: 
  - 大きな乖離 (>0.5) → 警告
  - 矛盾 (符号反転) → エラー
- 呼び出し: 執筆中定期的 (3シーンごと) または明示的指示時
- テスト: `tests/unit/agent/tools/test_consistency.py::test_detect_large_divergence`

**Step 16: 感情フック自動生成・提案**
- ファイル: `src/agent/hooks/hook_generator.py` (新規)
- 関数: `generate_hooks(core_memory: CoreMemory, plot_outline: str) -> List[str]`
- 例: "Aの恐怖(0.8)が解消されていない → 今話で恐怖の原因(B)と対峙させる"
- LLM 1回呼び出しで生成、CoreMemory の `active_hooks` にセット
- テスト: `tests/unit/agent/hooks/test_hook_generator.py::test_generate_hooks_from_fear`

**Step 17: キャラクター別「声」パーソナライゼーション**
- ファイル: `src/agent/memory/voice_profile.py` (新規)
- CoreMemory 追加フィールド: `voice_profiles: Dict[str, VoiceProfile]`
- `VoiceProfile`: `speech_patterns, vocabulary_level, emotional_leakage (内心が顔に出やすさ), lying_tendency`
- 執筆時: 該当キャラのセリフ生成前にプロファイル参照 → プロンプト注入
- 学習: 執筆済みセリフからパターン抽出 (ルールベース、Week 1 流用) → プロファイル更新
- テスト: `tests/unit/agent/memory/test_voice_profile.py::test_profile_influences_dialogue`

**Step 18: 分岐・IF 対応 (ブランチ別メモリ)**
- ファイル: `src/agent/memory/branch_manager.py` (新規)
- クラス: `BranchMemoryManager`
- 機能:
  - `fork_branch(base_branch, new_branch)`: CoreMemory ディープコピー
  - `merge_branch(source, target, strategy: "auto" | "manual")`: 競合時は手動解決
  - `compare_branches(branch1, branch2) -> Diff`: 感情状態差分表示
- ストレージ: `memory/{project}/{branch}/core_memory.json`
- テスト: `tests/unit/agent/memory/test_branch_manager.py::test_fork_and_compare`

**Step 19: パフォーマンス最適化・キャッシュ**
- ファイル: `src/agent/memory/cached_archival.py` (新規)
- クラス: `CachedArchivalMemory` (ArchivalMemory ラッパー)
- LRU キャッシュ: 検索クエリ埋め込み → 結果 (最大 100 エントリ)
- 埋め込み計算キャッシュ: 同一テキストは再計算スキップ
- 非同期プリフェッチ: 直近ペアの因果パスをバックグラウンド取得
- テスト: `tests/performance/test_cached_archival.py::test_cache_hit_rate`

**Step 20: 観測・デバッグ用メモリダンプ API**
- ファイル: `src/api/agent_memory.py` (新規)
- エンドポイント:
  - `GET /api/agent/memory/core` → CoreMemory 全内容
  - `GET /api/agent/memory/working` → WorkingMemory フレームスタック
  - `GET /api/agent/memory/archival/stats` → Archival 件数・サイズ
  - `POST /api/agent/memory/compact` → 強制圧縮実行
- 用途: 開発者ダッシュボード・デバッグ
- テスト: `tests/integration/api/test_agent_memory_api.py::test_core_memory_dump`

---

### Phase 4: 統合テスト・ドキュメント・リグレッション (Steps 21-24)

**Step 21: 完全統合リグレッションテスト**
- ファイル: `tests/regression/test_week5_regression.py` (新規)
- ケース:
  - `test_core_memory_persists_across_restarts`: 再起動で状態復元
  - `test_tool_calls_update_core_memory`: update_emotion で Core 更新
  - `test_archival_search_works`: recall_similar_scene で過去シーン検索
  - `test_compaction_moves_old_data`: 圧縮で Archival に移動
  - `test_fused_vector_injected`: Week 4 融合ベクトルが初期 CoreMemory に反映
  - `test_branch_isolation`: ブランチ分岐でメモリ独立
  - `test_voice_profile_affects_dialogue`: プロファイル反映確認

**Step 22: 既存 Week 1-4 テストの Agent 版対応**
- ファイル: `tests/integration/pipeline/test_full_pipeline.py` (既存編集)
- 修正: Writer Agent 使用時のプロンプト生成フローを Agent 版に切替確認
- 並列実行: `pytest -n auto` で全テストスイートパス確認

**Step 23: 負荷テスト・長時間稼働テスト**
- ファイル: `tests/stress/test_agent_longrun.py` (新規)
- シナリオ: 50話連続執筆シミュレーション (モック LLM)
- 検証:
  - メモリリークなこと (RSS 増加 < 100MB)
  - CoreMemory サイズ安定 (圧縮動作確認)
  - Archival 検索レイテンシ劣化なし (p99 < 200ms)
  - ツール呼び出し成功率 > 99%

**Step 24: Week 5 完了ドキュメント・アーキテクチャ決定記録 (ADR)**
- ファイル: `docs/emotional_state_cache_week5.md` (新規)
- ファイル: `docs/adr/001-agent-memory-architecture.md` (新規)
- 内容:
  - 3層メモリ設計理由・トレードオフ
  - CoreMemory スキーマ・トークン予算
  - Archival ストアマッピング (Week 1-4 再利用)
  - ツール設計指針 (LLM が呼びやすい粒度)
  - 圧縮ポリシー・チューニングパラメータ
  - 分岐対応・マルチプロジェクト運用
  - 既知の制限・将来拡張 (長期記憶・エピソード間推論等)

---

## 完了基準 (Definition of Done)

- [ ] 全 Step 1-24 テストパス (CI グリーン、ストレステスト含む)
- [ ] Writer Agent が CoreMemory を参照し、感情整合性のある執筆を行う
- [ ] `update_emotion` 等ツールが自律的に呼ばれ、CoreMemory 更新される
- [ ] 圧縮ポリシー動作: トークン超過時に古情報が Archival へ退避
- [ ] プロジェクト再起動で CoreMemory 完全復元
- [ ] Week 4 融合ベクトルが初期 CoreMemory に正しくロードされる
- [ ] ブランチ分岐でメモリ独立、マージ・比較可能
- [ ] 全リグレッションテスト (Week 1-5) パス
- [ ] ADR ドキュメントでアーキテクチャ決定理由が追跡可能