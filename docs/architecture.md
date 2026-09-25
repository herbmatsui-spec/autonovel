## 4. 4層圧縮モジュール (Compression Module)

AutoNovel の中核機能の一つとして、LLM プロンプト・過去文脈・キャラクター情報・世界観設定などを階層的に圧縮する `FourLayerCompressor` が実装されています。このモジュールは、プロンプトサイズの削減と重要情報の保持を両立し、コスト削減と生成品質の維持を目的としています。

### 4.1 構造

FourLayerCompressor は以下の4層から構成されます：

1. **Layer 1: キーワード抽出層**  
   - 入力テキストから重要キーワード（固有名詞・専門用語）を抽出し、重み付けを行います。
   - 出力: `RawTextLayerOutput`（抽出キーワード・スコア・元文字数等）

2. **Layer 2: サブグラフ層**  
   - 抽出キーワードをノードとし、共起関係や依存関係をエッジとしたサブグラフを構築します。  
   - プルーニングにより関係の薄いエッジを除去し、核となる関係構造を保持します。  
   - 出力: `SubgraphLayerOutput`（ノード・エッジ・シードエンティティ・統計情報）

3. **Layer 3: 抽象化層**  
   - サブグラフを概念レベルに変換し、カテゴリ化・概念の圧縮を行います。  
   - 出力: `AbstractionLayerOutput`（抽象概念・事実の分類・カテゴリマッピング・メタデータ）

4. **Layer 4: トリミング層**  
   - 抽象化結果を最終的なプロンプトテキストに変換し、不要な記述を除去しつつ、重要なエンティティ・事実・伏線を保持します。  
   - シーンタイプ（一般・戦闘・日常・心理・政治・ロマンス・ミステリー・フラッシュバック・サバイバル）に応じたトリミング戦略を適用します。  
   - 出力: `TrimmedContextOutput`（圧縮テキスト・トークン数・保持エンティティ・圧縮率・保持率等）

4. **品質メトリクス**  
   - 各層の出力から、キャラクター保持率・伏線保持率・固有名詞保持率・意味密度スコア・全体整合性スコアなどの品質指標を算出します（`CompressionQualityMetrics`）。

### 4.2 依存性注入 (DI)

- `FourLayerCompressor` は `src/core/container/app.py` の `AppContainer` にてシングルトンプロバイダーとして登録されています。
- `compression_config` プロバイダーにて `CompressionConfig` インスタンスを提供し、これを用いて `FourLayerCompressor` を生成します。
- 主なサービス・エージェントはコンストラクタ経由で `compressor: Any = None` を受け取り、DI コンテナから提供されたインスタンスを使用します。
  - `WritingService.__init__(..., compressor: Any = None)`
  - `ContextBuilderAgent.__init__(..., compressor: Any = None)`
  - `EpisodeWriter.__init__(..., compressor: Any = None)`
  - `create_easy_mode_pipeline(..., compressor: Any = None)`

### 4.3 主な利用箇所

- **WritingService**  
  - `_build_context_with_compression` メソッドにて、コンテキストに `compressor` を設定し、`ContextBuilderAgent.execute` を呼び出します。  
  - これにより、執筆品質評価プロセスで圧縮コンテキストが生成され、`writing_context` に `compressed_context` と `compression_stats` が格納されます。

- **ContextBuilderAgent**  
  - `execute` メソッドにて、`artifacts` から `compressor` を取得（または自分の `self.compressor` を使用）し、`_build_full_writing_context_internal` 内部で圧縮を適用します。  
  - 圧縮結果は `CompressedContextResult` として得られ、最終的に `writing_context` に格納されます。

- **EpisodeWriter**  
  - `build_context` メソッドにて、自身の `self.compressor` を `artifacts` に設定し、`ContextBuilderAgent.execute` を呼び出します。  
  - 圧縮コンテキストは同様に `writing_context` に格納されます。

- **EasyMode パイプライン**  
  - `create_easy_mode_pipeline` 関数にて、引数 `compressor` を受け取り、内部で `CompressionPipelineStep` または各ステップに渡します（実装詳細は `src/services/auto_workflow_pipeline.py` 参照）。

### 4.5 使用例（DI コンテナから取得）

```python
from src.core.container.app import AppContainer
container = AppContainer()
compressor = container.compressor()  # FourLayerCompressor インスタンス
# またはサービス経由で取得
writing_service = container.writing_service()
# writing_service.compressor 経由でアクセス可能
```

### 4.6 設定

`CompressionConfig` インスタンスにて以下のパラメータを調整可能です（デフォルト値は `src/services/compression/models.py` 参照）：

- `max_tokens`: 最大出力トークン数（デフォルト 1500）
- `target_reduction_ratio`: 目標圧縮率（デフォルト 0.6）
- `top_keywords`: 抽出するキーワード数上限（デフォルト 20）
- `max_hops`: サブグラフ探索の最大ホップ数（デフォルト 2）
- `relevance_threshold`: エッジ保持の関連性閾値（デフォルト 0.5）
- `scene_type`: デフォルトシーンタイプ（デフォルト "general"）
- `cache_enabled`: 結果キャッシュの有無（デフォルト True）
- `cache_ttl_seconds`: キャッシュ有効時間（秒、デフォルト 3600）
- `preserve_categories`: 優先保持するカテゴリリスト（デフォルト ["主要キャラ", "核心設定", "伏線"]）

### 4.7 テスト

- 単体テスト: `tests/unit/test_four_layer_compression.py`
- 契約テスト: `tests/contract/test_compression_output_schema.py`
- プロパティベーステスト: `tests/property/test_compression_invariants.py`
- 性能ベンチマーク: `tests/performance/test_compression_benchmark.py`
- E2E テスト: `tests/e2e/test_full_novel_with_compression.py`

全テストは CI パイプラインで自動実行されます.