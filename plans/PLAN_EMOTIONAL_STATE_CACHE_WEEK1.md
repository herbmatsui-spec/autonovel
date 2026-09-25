# PLAN: 感情状態キャッシュ Week 1 - ルールベース抽出＋Vector注入
**目標**: エピソード終了時にルールベースで感情ベクトル抽出 → Redis Vector保存 → 次話プロンプト冒頭に自動注入
**前提**: 既存パイプライン `CompressionPipeline` にステージ追加のみ。LLM呼び出しなし。

---

## Step 1-24 実装タスク

### Phase 1: データ構造・インターフェース定義 (Steps 1-4)

**Step 1: 感情ベクトルデータクラス作成**
- ファイル: `src/pipeline/emotional_residue.py` (新規)
- クラス: `EmotionalVector`, `EmotionalSignal`, `EmotionType` (Enum)
- フィールド: source, target, emotion_type, value(-1.0~1.0), confidence, evidence_span, episode_id
- テスト: `tests/unit/pipeline/test_emotional_residue.py::test_emotional_vector_creation`

**Step 2: 感情辞書・パターン定義ファイル作成**
- ファイル: `config/emotion_lexicon.yaml` (新規)
- 構造: `affection: {positive: [...], negative: [...]}`, `tension: {...}`, `fear: {...}`, `trust: {...}`, `intimacy: {...}`
- 共起パターン: `dependency_patterns` リスト
- テスト: `tests/unit/config/test_emotion_lexicon.py::test_lexicon_loads_correctly`

**Step 3: 設定ローダー実装**
- ファイル: `src/pipeline/emotion_config.py` (新規)
- 関数: `load_emotion_lexicon() -> EmotionLexicon`, `load_dependency_patterns() -> List[DependencyPattern]`
- シングルトンパターンでキャッシュ
- テスト: `tests/unit/pipeline/test_emotion_config.py::test_singleton_behavior`

**Step 4: Vectorストアインターフェース定義**
- ファイル: `src/stores/vector_store.py` (新規)
- クラス: `VectorStore` (ABC), `RedisVectorStore` (実装)
- メソッド: `upsert(namespace: str, key: str, vector: EmotionalVector)`, `get_latest(namespace: str, pair: Tuple[str,str]) -> EmotionalVector`, `get_all(namespace: str) -> List[EmotionalVector]`
- TTL設定: `namespace` ごとに設定可能
- テスト: `tests/unit/stores/test_vector_store.py::test_upsert_and_get_latest`

---

### Phase 2: ルールベース抽出器実装 (Steps 5-12)

**Step 5: GiNZA/NLPパイプライン初期化**
- ファイル: `src/pipeline/nlp_init.py` (新規)
- 関数: `get_nlp() -> spacy.Language` (シングルトン)
- モデル: `ja_ginza` または `ja_core_news_lg`
- テスト: `tests/unit/pipeline/test_nlp_init.py::test_nlp_singleton`

**Step 6: キャラクター名抽出器**
- ファイル: `src/pipeline/character_extractor.py` (新規)
- クラス: `CharacterExtractor`
- メソッド: `extract(doc: Doc, character_dict: Set[str]) -> List[CharacterMention]`
- 固有表現(PERSON) + キャラ辞書マッチ + 代名詞解決(簡易)
- テスト: `tests/unit/pipeline/test_character_extractor.py::test_extract_known_characters`

**Step 7: 依存構造ベース感情シグナル抽出**
- ファイル: `src/pipeline/signal_extractor.py` (新規)
- クラス: `SignalExtractor`
- メソッド: `extract_signals(doc: Doc, characters: List[CharacterMention], lexicon: EmotionLexicon) -> List[EmotionalSignal]`
- ロジック: ROOT動詞の nsubj/dobj/iobj から主語-目的語ペア取得 → 語彙マッチで感情判定
- テスト: `tests/unit/pipeline/test_signal_extractor.py::test_extract_affection_signal`

**Step 8: 感情極性判定関数**
- ファイル: `src/pipeline/polarity.py` (新規)
- 関数: `classify_emotion(verb_token: Token, sent_text: str, lexicon: EmotionLexicon) -> Tuple[EmotionType, float]`
- 正負語彙カウント → 強度計算 (0.3 + 0.2 * diff, clamp 1.0)
- テスト: `tests/unit/pipeline/test_polarity.py::test_positive_affection`, `test_negative_fear`

**Step 9: シグナル集約・正規化**
- ファイル: `src/pipeline/aggregator.py` (新規)
- 関数: `aggregate_signals(signals: List[EmotionalSignal]) -> EmotionalVector`
- 同一(source, target, emotion)の重み付き平均 (confidence重み)
- 値を -1.0~1.0 にクランプ
- テスト: `tests/unit/pipeline/test_aggregator.py::test_aggregate_multiple_signals`

**Step 10: メイン抽出器クラス統合**
- ファイル: `src/pipeline/emotional_residue.py` (Step 1 のファイルに追加)
- クラス: `EmotionalResidueExtractor`
- `__init__(vector_store: VectorStore, character_dict: Set[str])`
- メソッド: `extract_and_persist(episode_id: str, script: str) -> EmotionalVector`
- 内部フロー: NLP → キャラ抽出 → シグナル抽出 → 集約 → VectorStore.upsert
- テスト: `tests/unit/pipeline/test_emotional_residue_extractor.py::test_extract_and_persist`

**Step 11: キャラクター辞書ローダー**
- ファイル: `src/pipeline/character_dict.py` (新規)
- 関数: `load_character_dict(path: str) -> Set[str]`
- 形式: YAML/JSON リスト、プロジェクトルート `config/characters.yaml` から読み込み
- テスト: `tests/unit/pipeline/test_character_dict.py::test_load_yaml`

**Step 12: 抽出器ユニットテスト総合**
- ファイル: `tests/unit/pipeline/test_emotional_residue_integration.py` (新規)
- フィクスチャ: 短いサンプル脚本 (3-5発話)
- アサーション: 主要ペアの感情タイプ・極性・概ねの値レンジ
- カバレッジ目標: 80%以上

---

### Phase 3: パイプライン統合 (Steps 13-16)

**Step 13: 既存 CompressionPipeline へのステージ追加**
- ファイル: `src/pipeline/compression_pipeline.py` (既存編集)
- インポート: `EmotionalResidueExtractor`
- `__init__` に `emotional_extractor` パラメータ追加 (Optional)
- `run()` メソッド内で `episode_end` 後に `extractor.extract_and_persist()` 呼び出し
- テスト: `tests/unit/pipeline/test_compression_pipeline_integration.py::test_emotional_stage_runs`

**Step 14: パイプライン設定への感情抽出有効化フラグ**
- ファイル: `config/pipeline.yaml` (既存編集)
- 追加: `emotional_residue: {enabled: true, vector_namespace: "pipeline"}`
- 設定読み込み箇所で条件分岐
- テスト: `tests/unit/config/test_pipeline_config.py::test_emotional_residue_config`

**Step 15: Redis接続設定追加**
- ファイル: `config/redis.yaml` (既存または新規)
- キー: `host, port, db, password, ttl_default: 864000` (10日)
- 環境変数対応: `REDIS_URL`
- テスト: `tests/unit/config/test_redis_config.py::test_redis_config_loads`

**Step 16: 統合テスト (パイプライン実行→Vector保存確認)**
- ファイル: `tests/integration/pipeline/test_emotional_residue_e2e.py` (新規)
- モック: Redis (fakeredis), NLP (小さなテスト用モデル)
- 入力: 既存テスト用脚本データ
- 検証: Redis に `ep:{episode_id}:{pair}` キーで保存されること

---

### Phase 4: プロンプト注入機能 (Steps 17-20)

**Step 17: 感情ベクトル自然言語化テンプレート**
- ファイル: `templates/emotional_context.j2` (新規)
- 入力: `EmotionalVector` (主要ペア上位5件)
- 出力例: 
  ```
  [直前話からの引き継ぎ感情]
  A→B: 表向きは感謝(0.3)だが、内心では底知れぬ恐怖(0.8)を抱いている (原因: 第14話の裏切り事件)
  B→A: 罪悪感(0.6)と警戒心(0.4)が混在
  ```
- テスト: `tests/unit/templates/test_emotional_context.py::test_render_basic`

**Step 18: プロンプトビルダー関数**
- ファイル: `src/pipeline/prompt_builder.py` (新規または既存編集)
- 関数: `build_emotional_context_prompt(episode_id: int, vector_store: VectorStore) -> str`
- ロジック: 次話番号から前話ID算出 → Vector取得 → テンプレート描画
- テスト: `tests/unit/pipeline/test_prompt_builder.py::test_build_prompt`

**Step 19: final_writing_prompt.j2 への注入ポイント追加**
- ファイル: `templates/final_writing_prompt.j2` (既存編集)
- 追加位置: `system` プロンプト冒頭 (最初の `{{ system_prompt }}` の直前)
- 変数: `{{ emotional_context }}` を挿入
- テスト: `tests/unit/templates/test_final_writing_prompt.py::test_emotional_context_injected`

**Step 20: 書き込みプロンプト生成フローへの統合**
- ファイル: `src/agents/writer_agent.py` またはプロンプト生成箇所 (既存編集)
- 呼び出し: `build_emotional_context_prompt(current_episode - 1, vector_store)`
- 生成プロンプトに `emotional_context` として渡す
- テスト: `tests/integration/agent/test_writer_prompt_injection.py::test_emotional_context_in_prompt`

---

### Phase 5: 設定・ドキュメント・リグレッションテスト (Steps 21-24)

**Step 21: 環境変数・設定ファイル例追加**
- ファイル: `.env.example` (既存編集)
- 追加: `REDIS_URL=redis://localhost:6379/0`
- ファイル: `config/characters.yaml.example` (新規)
- 内容: サンプルキャラ名リスト

**Step 22: リグレッションテストスイート追加**
- ファイル: `tests/regression/test_emotional_residue_regression.py` (新規)
- テストケース:
  - `test_no_regression_basic_extraction`: 既知サンプルで期待値と一致
  - `test_no_regression_prompt_injection`: プロンプトに感情文言が含まれる
  - `test_no_regression_vector_persistence`: 再起動後も Vector 読み出し可能
  - `test_no_regression_ttl_expiry`: TTL経過でキー消失確認 (モック時間)

**Step 23: CI/CD パイプライン追加**
- ファイル: `.github/workflows/emotional_residue.yml` (新規)
- ジョブ: `unit-tests`, `integration-tests`, `regression-tests`
- トリガー: `paths: ['src/pipeline/**', 'config/emotion_lexicon.yaml', 'templates/emotional_context.j2']`
- 実行: `pytest tests/unit/pipeline/ tests/integration/pipeline/ tests/regression/test_emotional_residue_regression.py`

**Step 24: 動作確認チェックリスト・ドキュメント**
- ファイル: `docs/emotional_residue_week1.md` (新規)
- 内容: 
  - 依存関係インストール手順 (`pip install spacy ginza redis fakeredis`)
  - 設定ファイル配置場所
  - 手動実行コマンド例
  - 期待される出力例
  - よくあるエラーと対処

---

## 完了基準 (Definition of Done)

- [ ] 全 Step 1-24 のテストがパス (CI グリーン)
- [ ] 手動実行で: 脚本入力 → Vector保存 → 次話プロンプトに感情文言注入 が確認できる
- [ ] リグレッションテスト 4ケース全パス
- [ ] カバレッジ: `src/pipeline/emotional_residue.py` 80%以上
- [ ] ドキュメントに従い新規環境で動作確認完了