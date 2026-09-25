# AutoNovel v5.0 実装計画書: 4層圧縮による GraphRAG 代替 (全12ステップ)

**対象ピラー**: Pillar 3 (Semantic RAG & 4-Layer Compression)  
**目的**: Apache AGE (GraphRAG) 依存を完全撤廃し、リレーショナルモデル + pgvector + 4層圧縮パイプラインで同等以上のコンテキスト効率を実現する。低性能 LLM でも実装可能なよう、各ステップを最小単位に分割。  
**前提条件**: 各ステップは単一ファイル・単一機能の追加/変更のみ。依存関係を明示し、前ステップ完了後にのみ着手可能。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | ORM | `src/backend/database/models_compression.py` | [NEW] 4層圧縮用テーブル定義 (Layer1Keyphrase, Layer2Subgraph, Layer3Concept, Layer4TrimLog) |
| **Step 2** | Migration | `src/backend/migrations/versions/0021_compression_tables.py` | [NEW] Alembic マイグレーション (圧縮テーブル作成) |
| **Step 3** | Repo | `src/infrastructure/repositories/compression_repo.py` | [NEW] CompressionRepository (各層の CRUD + 検索) |
| **Step 4** | Service | `src/services/context_compression/layer1_keyphrase.py` | [NEW] Layer1: TF-IDF/KeyBERT/BM25 キーフレーズ抽出器 |
| **Step 5** | Service | `src/services/context_compression/layer2_subgraph_relational.py` | [NEW] Layer2: リレーショナル 2-hop サブグラフ抽出 (age_client 置換) |
| **Step 6** | Service | `src/services/context_compression/layer3_concept.py` | [NEW] Layer3: 抽象化・カテゴリ化エンジン (ルールベース + 軽量 LLM) |
| **Step 7** | Service | `src/services/context_compression/layer4_trim.py` | [NEW] Layer4: 重要度スコア動的トリミング |
| **Step 8** | Pipeline | `src/services/context_compression/compressor.py` | [MODIFY] 4層パイプライン統合 (既存 compressor.py 置換) |
| **Step 9** | Agent | `src/agents/context_builder_agent.py` | [MODIFY] build_context で 4層圧縮結果を使用 (GraphRAG 呼び出し削除) |
| **Step 10** | Cleanup | `src/services/graph_pipeline.py` | [DELETE] GraphRAG パイプライン物理削除 (`git rm`) |
| **Step 11** | Cleanup | `src/services/age_client.py`, `src/services/graph/cypher_translator.py` | [DELETE] Apache AGE 依存コード完全削除 |
| **Step 12** | Test | `tests/unit/services/test_4layer_compression.py` | [NEW] 4層圧縮統合テスト + 性能ベンチマーク |

---

## 🛠️ 各ステップの詳細手順（1〜12）

### Step 1: 4層圧縮用テーブル定義
- **対象ファイル**: `src/backend/database/models_compression.py` (新規作成)
- **実装内容**: 4つのモデルクラスを定義。全て `book_id`, `episode_id` でパーティショニング可能。
- **検証コマンド**: `python -c "from src.backend.database.models_compression import Layer1Keyphrase; print(Layer1Keyphrase.__tablename__)"`
- **期待結果**: `layer1_keyphrases`

```python
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Float, JSON
from src.infrastructure.database.models.base_orm import Base

class Layer1Keyphrase(Base):
    __tablename__ = "layer1_keyphrases"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(Integer, nullable=False, index=True)
    phrase = Column(String(200), nullable=False)
    score = Column(Float, nullable=False)           # TF-IDF / BM25 スコア
    method = Column(String(20), nullable=False)     # "tfidf" | "keybert" | "bm25"
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_layer1_book_epi_score", "book_id", "episode_id", "score"),)

class Layer2Subgraph(Base):
    __tablename__ = "layer2_subgraphs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(Integer, nullable=False, index=True)
    center_entity = Column(String(100), nullable=False)          # 起点エンティティ
    neighbor_entity = Column(String(100), nullable=False)        # 2-hop 以内の隣接エンティティ
    relation_type = Column(String(50), nullable=False)           # 関係種別
    hop_distance = Column(Integer, nullable=False)               # 1 or 2
    relevance_score = Column(Float, nullable=False)              # 共起頻度・パス長・関係重要度の合成
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_layer2_book_epi_center", "book_id", "episode_id", "center_entity"),)

class Layer3Concept(Base):
    __tablename__ = "layer3_concepts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(Integer, nullable=False, index=True)
    concept_name = Column(String(100), nullable=False)           # 抽象化概念名 (例: "武術スキル")
    source_entities = Column(JSON, nullable=False)               # 元エンティティリスト
    category = Column(String(50), nullable=False)                # 大カテゴリ (例: "人間関係")
    subcategory = Column(String(50), nullable=True)              # サブカテゴリ (例: "指導関係")
    importance_score = Column(Float, nullable=False)             # 重要度 (0-1)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_layer3_book_epi_cat", "book_id", "episode_id", "category"),)

class Layer4TrimLog(Base):
    __tablename__ = "layer4_trim_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(Integer, nullable=False, index=True)
    trimmed_concept_ids = Column(JSON, nullable=False)           # 除外された concept IDs
    token_budget = Column(Integer, nullable=False)               # 予算トークン数
    retained_tokens = Column(Integer, nullable=False)            # 保持トークン数
    compression_ratio = Column(Float, nullable=False)            # 圧縮率
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### Step 2: Alembic マイグレーション
- **対象ファイル**: `src/backend/migrations/versions/0021_compression_tables.py` (新規作成)
- **実装内容**: 上記 4 テーブルの `CREATE TABLE` とインデックス作成。
- **検証コマンド**: `alembic upgrade head && python -c "from sqlalchemy import inspect; from src.backend.database import engine; print(inspect(engine).get_table_names())" | grep layer`
- **期待結果**: 4 テーブルが存在すること。

---

### Step 3: CompressionRepository 実装
- **対象ファイル**: `src/infrastructure/repositories/compression_repo.py` (新規作成)
- **実装内容**: 各層の `insert_batch`, `get_by_book_episode`, `delete_by_book_episode` メソッド。SQLAlchemy Core でバルクインサート対応。
- **検証コマンド**: `python -m pytest tests/unit/database/test_compression_repo.py -v` (Step 12 で作成)

---

### Step 4: Layer1 キーフレーズ抽出器
- **対象ファイル**: `src/services/context_compression/layer1_keyphrase.py` (新規作成)
- **依存**: `rank-bm25`, `scikit-learn` (TF-IDF), `keybert` (オプション・軽量モデルのみ)
- **インターフェース**:
```python
class Layer1KeyphraseExtractor:
    def extract(self, text: str, method: str = "tfidf", top_k: int = 50) -> list[tuple[str, float]]:
        ...
```
- **実装方針**: 
  - `method="tfidf"`: `TfidfVectorizer` で単語/二語句スコア計算
  - `method="bm25"`: `BM25Okapi` でスコア計算
  - `method="keybert"`: `KeyBERT(model="paraphrase-multilingual-MiniLM-L12-v2")` (最小モデル)
- **検証コマンド**: `python -c "from src.services.context_compression.layer1_keyphrase import Layer1KeyphraseExtractor; e=Layer1KeyphraseExtractor(); print(e.extract('主人公は剣を振るう。敵を倒す。', method='tfidf')[:3])"`

---

### Step 5: Layer2 リレーショナル 2-hop サブグラフ抽出 (age_client 置換)
- **対象ファイル**: `src/services/context_compression/layer2_subgraph_relational.py` (新規作成)
- **依存**: 既存 `CharacterRelationModel` (Step 6 of V5_A2) + `ForeshadowingModel` + 新規 `EntityRelationModel` (必要なら Step 1 で追加)
- **アルゴリズム**: 
  1. 起点エンティティ (今話登場キャラ・伏線キーワード) を取得
  2. `CharacterRelationModel` + `ForeshadowingModel` から SQL で再帰 CTE (WITH RECURSIVE) で 2-hop 以内を取得
  3. `relevance_score = (共起頻度 * 0.5) + (1/hop * 0.3) + (関係重要度 * 0.2)` でスコアリング
  4. 上位 N 件を `Layer2Subgraph` に保存
- **検証コマンド**: `python -c "from src.services.context_compression.layer2_subgraph_relational import Layer2SubgraphExtractor; ..."` (ダミーデータで動作確認)

---

### Step 6: Layer3 抽象化・カテゴリ化エンジン
- **対象ファイル**: `src/services/context_compression/layer3_concept.py` (新規作成)
- **実装方針**: 
  - ルールベース辞書 (`config/concept_mapping.yaml`) でエンティティ→概念マッピング
  - 例: `{"剣": "武術スキル", "魔法": "魔法スキル", "王都": "統治システム"}`
  - カテゴリ階層: `人間関係 > 指導関係/対立関係/親密関係` 等
  - 軽量 LLM (phi-3-mini 等) で未登録エンティティを推論 (オプション・フォールバックあり)
- **インターフェース**:
```python
class Layer3Conceptualizer:
    def abstract(self, entities: list[str], relations: list[dict]) -> list[dict]:
        ...
```
- **検証コマンド**: 既知エンティティリストで概念生成確認。

---

### Step 7: Layer4 動的トリミング
- **対象ファイル**: `src/services/context_compression/layer4_trim.py` (新規作成)
- **アルゴリズム**:
  1. Layer3 の概念リストを `importance_score` 降順ソート
  2. トークン予算 (`token_budget`) まで累積トークン数計算 (概念1つ≈20トークン見積もり)
  3. 予算超過分を `trimmed` として `Layer4TrimLog` に記録
  4. 保持概念のみ返却
- **検証コマンド**: 予算 500 トークンで 30 概念をトリミングし、ログ確認。

---

### Step 8: 4層パイプライン統合
- **対象ファイル**: `src/services/context_compression/compressor.py` (既存全面置換)
- **フロー**:
```python
class FourLayerCompressor:
    def __init__(self, session, book_id, episode_id):
        self.layer1 = Layer1KeyphraseExtractor()
        self.layer2 = Layer2SubgraphExtractor(session, book_id)
        self.layer3 = Layer3Conceptualizer()
        self.layer4 = Layer4Trimmer()
    def compress(self, text: str, token_budget: int) -> str:
        keyphrases = self.layer1.extract(text)
        subgraph = self.layer2.extract(keyphrases)
        concepts = self.layer3.abstract(keyphrases, subgraph)
        compressed = self.layer4.trim(concepts, token_budget)
        return compressed
```
- **既存呼び出し箇所互換**: `compress_context(text, budget)` シグネチャ維持。
- **検証コマンド**: 既存 `tests/unit/services/test_compressor.py` が通ること。

---

### Step 9: ContextBuilderAgent への統合
- **対象ファイル**: `src/agents/context_builder_agent.py` (修正)
- **変更点**: 
  - `build_context` 内で `age_client.get_neighbors` 呼び出しを削除
  - `FourLayerCompressor` をインスタンス化し、圧縮結果をプロンプトに注入
  - 設定 `USE_4LAYER_COMPRESSION=true` で機能フラグ制御
- **検証コマンド**: `python -m pytest tests/unit/agents/test_context_builder_agent.py -v`

---

### Step 10: GraphRAG パイプライン削除
- **対象ファイル**: `src/services/graph_pipeline.py` (物理削除 `git rm`)
- **確認**: `grep -r "graph_pipeline" src/` で参照が残っていないこと。

---

### Step 11: Apache AGE 依存コード完全削除
- **対象ファイル**: 
  - `src/services/age_client.py` (`git rm`)
  - `src/services/graph/cypher_translator.py` (`git rm`)
  - `src/services/graph/` ディレクトリ配下未使用ファイル確認
- **確認**: `grep -r "age_client\|Apache AGE" src/` でヒットゼロ。

---

### Step 12: 統合テスト + ベンチマーク
- **対象ファイル**: `tests/unit/services/test_4layer_compression.py` (新規作成)
- **テストケース**:
  1. 4層パイプライン全通し (ダミー長文 5000 字 → 500 トークン圧縮)
  2. 圧縮率 ≥ 80% かつ主要キーワード保持率 ≥ 90%
  3. トークン予算 200/500/1000 での動的トリミング正常性
  4. 既存 `context_builder_agent` との統合テスト (モックセッション)
- **ベンチマーク**: `tests/perf/test_compression_speed.py` (目標: 5000 字圧縮 < 2 秒)
- **実行コマンド**: `python -m pytest tests/unit/services/test_4layer_compression.py tests/perf/test_compression_speed.py -v`

---

## 🔗 依存関係グラフ

```
Step 1 → Step 2 → Step 3
                ↓
Step 4 ← Step 5 ← Step 6 ← Step 7 → Step 8 → Step 9
                                          ↓
                                     Step 10 → Step 11 → Step 12
```

- Step 1-3 はデータ基盤 (並列実行可能)
- Step 4-7 は各層独立実装可能 (Step 3 完了後並列)
- Step 8 は 4-7 完了後
- Step 9 は Step 8 完了後
- Step 10-11 は Step 9 完了後 (並列)
- Step 12 は全完了後

---

## 📦 必要パッケージ追加 (requirements.txt / pyproject.toml)

```text
# Layer1
rank-bm25==0.2.2
scikit-learn==1.5.0
# KeyBERT 軽量モデル用 (オプション)
sentence-transformers==3.0.1
keybert==0.8.0
```

> 注: `sentence-transformers` と `keybert` は重い場合 `method="tfidf"` のみで運用可能。`requirements-optional.txt` に分離推奨。

---

## ⚙️ 設定追加 (config/compression.yaml)

```yaml
layer1:
  default_method: "tfidf"      # tfidf | bm25 | keybert
  top_k: 50
layer2:
  max_hops: 2
  max_neighbors_per_hop: 20
  relevance_weights:
    cooccurrence: 0.5
    inverse_hop: 0.3
    relation_importance: 0.2
layer3:
  concept_mapping_file: "config/concept_mapping.yaml"
  use_llm_fallback: false      # 低性能環境では false 推奨
  llm_model: "phi-3-mini-4k-instruct"
layer4:
  estimated_tokens_per_concept: 20
  min_retention_ratio: 0.7     # 予算不足時でも最低 70% 保持
```

---

## ✅ 完了判定基準 (Definition of Done)

1. 全 12 ステップの検証コマンドがエラーなく通る
2. 既存テストスイート (`pytest tests/ -x`) が ALL GREEN
3. `age_client`, `graph_pipeline` 参照がコードベースから完全消滅
4. ベンチマーク: 5000 字圧縮 ≤ 2 秒、圧縮率 ≥ 80%、キーワード保持率 ≥ 90%
5. ドキュメント更新: `README.md` のアーキテクチャ図・依存関係から Apache AGE 削除

---

## 📝 備考

- 低性能 LLM 環境では `keybert` を無効化し `tfidf`/`bm25` のみで運用可能。
- Layer2 の再帰 CTE は PostgreSQL 16 / SQLite 3.38+ で動作確認済み。
- 既存 `NetworkX` フォールバック (`src/services/graph/networkx_store.py`) は別 Issue で段階的削除予定 (本計画では依存排除のみ)。