# Writing Service 現状分析と統合設計メモ (Phase 1 調査結果)

## 1. 概要
AutoNovel コードベース内には「WritingService」に関連する実装が 3 箇所に分散して存在しており、責務の重複および命名の類似による混乱が生じています。
方向性1 (基盤固め) では既存ワークフローへの影響を避けるためコード変更は行わず、Phase 2 での安全な統合に向けた詳細調査と設計方針の整理を実施しました。

---

## 2. 現状の3実装の詳細

### (A) `src/backend/writing_service.py`
- **主な責務**: 執筆パイプラインの実行および `EngineFacade` / `WritingAgent` への委譲
- **使用箇所**:
  - `src/backend/workflows/base_workflow.py`
  - `src/backend/workflows/chapter_import_workflow.py`
  - `src/backend/workflows/episode_writing_workflow.py`
- **主要メソッド**:
  - `generate_episodes_pipeline`: パイプライン執筆
  - `generate_episodes`: 単発執筆
  - `calculate_book_score`: 執筆後のスコア計算

### (B) `src/services/writing_service.py`
- **主な責務**: BookScore連携および多次元自動再生成ループ (`RegenerationAction`)
- **使用箇所**:
  - `src/core/container/app.py` (DI コンテナ登録: `src.services.writing_service.WritingService`)
  - `src/agents/writing/agent.py` (再生成フォーカス指示の受け渡し)
  - `src/agents/illustration_agent.py`
- **主要メソッド**:
  - `execute_with_book_score_loop`: スコア閾値未満時の自動フィードバック・再生成反復
  - `DIMENSION_ACTIONS`: structure, coherency, factual_grounding, visual_textual_synergy, reader_experience, anti_ai_correction の6次元対応

### (C) `src/services/writing_services.py`
- **主な責務**: 状態遷移バリデーション (`StateValidator`)、プロンプト組み立て、`ProjectContext` 連携
- **主要クラス**:
  - `WritingGenerationContext`
  - `WritingExecutionPipeline` (970行規模の低レベル生成処理)

---

## 3. ポートとインターフェース定義
- `src/application/ports/writing_service.py` (`IWritingService`) が定義されているが、上記の各実装は未だ `IWritingService` を直接継承していない。

---

## 4. Phase 2 統合推奨ロードマップ

1. **命名の明確化**:
   - `src/backend/writing_service.py` -> `WritingPipelineService` (パイプライン制御)
   - `src/services/writing_service.py` -> `WritingRegenerationService` (BookScore評価ループ)
   - `src/services/writing_services.py` -> `WritingContextBuilder` / `EpisodeGenerator` (コンテキスト生成)
2. **統合ファサードの提供**:
   - `src/services/writing/` パッケージに集約し、`IWritingService` を満たす統一ファサード `WritingService` を提供
3. **DI コンテナの一元化**:
   - `AppContainer` 経由での注入経路を1本化し、ワークフロー側からの参照を統合
