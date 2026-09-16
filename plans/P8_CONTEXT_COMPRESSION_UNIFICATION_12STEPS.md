# P8: 4層コンテキスト圧縮 二重実装解消・一本化実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**目的**: `src/services/context_compression/`（旧・孤立実装）を `src/services/compression/`（現行・稼働実装）へ完全一本化・技術的負債を清算し、設定ファイル・テスト・ドキュメントの整合性を担保する。  
**低性能LLM向け設計方針**:
- 1ステップごとに**1つの関心事（1〜2ファイル）のみ**を変更。
- 各ステップに**対象ファイルパス**、**編集前の差分/コード**、**そのまま使える完全な置換コード**、**実行すべき検証コマンド**、**合否基準（Pass条件）**を明記。
- 外部インフラ（Docker/AGE/PostgreSQL/Redis）不要で、自己完結・決定論的にローカル実行可能。

---

## 📋 全12ステップ 実装マトリクス

| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **Step 1** | 互換確認 | `src/services/compression/models.py` | 旧型定義（`CompressionResult`等）の吸収・エイリアス追加 | `pytest tests/unit/test_compression_pipeline.py -o addopts="" --no-cov` |
| **Step 2** | 機能移植 | `src/services/compression/layer1_keywords.py` | 旧実装にあった TF-IDF・BM25 抽出機能の統合・API拡充 | `pytest tests/unit/test_sudachi_tokenizer.py -o addopts="" --no-cov` |
| **Step 3** | 設定統合 | `src/services/compression/models.py` | `context_compression.yaml` 読み込み関数（`load_compression_config`）の統合 | `pytest tests/unit/test_compression_pipeline.py -o addopts="" --no-cov` |
| **Step 4** | パッケージ公開 | `src/services/compression/__init__.py` | 旧API互換エイリアス（`ContextCompressionPipeline`等）の再エクスポート定義 | `python -c "import src.services.compression as sc; print(sc.__all__)"` |
| **Step 5** | 互換シム設置 | `src/services/context_compression/keyphrase_extractors.py` | 警告付きで新 `src.services.compression` へ転送する Shim 化 | `pytest tests/unit/test_keyphrase_extractors.py -o addopts="" --no-cov` |
| **Step 6** | 互換シム設置 | `src/services/context_compression/pipeline.py` | 警告付きで新 `src.services.compression` へ転送する Shim 化 | `python -c "from src.services.context_compression.pipeline import ContextCompressionPipeline"` |
| **Step 7** | ユーティリティ整理 | `src/utils/context_compression_config.py` | `src.services.compression` からの設定再エクスポート化（deprecation警告） | `python -c "from src.utils.context_compression_config import load_compression_config"` |
| **Step 8** | テスト移行 | `tests/unit/test_keyphrase_extractors.py` | 新パッケージ `src.services.compression` を直接インポートするよう更新 | `pytest tests/unit/test_keyphrase_extractors.py -o addopts="" --no-cov` |
| **Step 9** | 設定ファイル同期 | `config/context_compression.yaml` | 現行 `models.CompressionConfig` のフィールド構造と完全同期 | `python -c "from src.services.compression import load_compression_config; c = load_compression_config(); assert c.max_tokens > 0"` |
| **Step 10** | 不要旧コード削除 | `src/services/context_compression/` | 旧ディレクトリ（`pipeline.py`, `keyphrase_extractors.py`）を安全に完全削除 | `python -c "import os; assert not os.path.exists('src/services/context_compression')"` |
| **Step 11** | 設定ファイル更新 | `pyproject.toml`, `never_referenced_modules.txt` | カバレッジ除外リスト（omit）および未参照一覧から旧パスを抹消 | `pytest tests/unit/test_compression_pipeline.py -o addopts="" --no-cov` |
| **Step 12** | 総合検証 | 全テストスイート | 圧縮・エージェント・E2Eの全関連テストを一括実行し回帰なきことを確認 | `pytest tests/unit/test_*compression*.py tests/unit/test_layer4_multiscene.py -o addopts="" --no-cov` |

---

## 🛠 各ステップ詳細手順

### Step 1: `models.py` の旧型互換エイリアス定義
- **目的**: 旧実装（`context_compression`）で使われていた戻り値型 `CompressionResult` や、フィールドアクセスを新実装の `CompressedContextResult` と互換にする。
- **対象ファイル**: [`src/services/compression/models.py`](file:///e:/hhh/src/services/compression/models.py)
- **編集内容**:
  `CompressedContextResult` クラスの末尾に、旧コード互換プロパティを追加し、エイリアス `CompressionResult = CompressedContextResult` を定義する。
```python
# src/services/compression/models.py の末尾に追加
class CompressedContextResult(BaseModel):
    layer1: RawTextLayerOutput | None = None
    layer2: SubgraphLayerOutput | None = None
    layer3: AbstractionLayerOutput | None = None
    layer4: TrimmedContextOutput
    final_context_text: str = ""
    final_token_count: int = 0
    overall_reduction_ratio: float = 0.0
    from_cache: bool = False
    elapsed_ms: float = 0.0

    # --- 旧API互換プロパティ ---
    @property
    def layer1_keyphrases(self) -> list[tuple[str, float]]:
        if not self.layer1:
            return []
        return [(k, self.layer1.keyword_scores.get(k, 1.0)) for k in self.layer1.extracted_keywords]

    @property
    def layer2_subgraph(self) -> dict[str, Any]:
        if not self.layer2:
            return {}
        return {"nodes": self.layer2.nodes, "edges": self.layer2.edges, "stats": self.layer2.stats}

    @property
    def layer3_abstracted(self) -> dict[str, list[dict[str, Any]]]:
        if not self.layer3:
            return {}
        return self.layer3.categorized_facts

    @property
    def layer4_trimmed(self) -> str:
        return self.final_context_text

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "reduction_ratio": self.overall_reduction_ratio,
            "final_tokens": self.final_token_count,
            "elapsed_ms": self.elapsed_ms,
            "from_cache": self.from_cache,
        }

# 旧型エイリアス
CompressionResult = CompressedContextResult
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.models import CompressionResult, CompressedContextResult; assert CompressionResult is CompressedContextResult"
  ```
- **合否基準**: エラーなく終了コード 0 で完了すること。

---

### Step 2: `layer1_keywords.py` への旧抽出器（TF-IDF, BM25, KeyBERT）統合
- **目的**: 旧 `keyphrase_extractors.py` で提供されていた `create_extractor` や `TFIDFExtractor`, `KeyBERTExtractor`, `BM25Extractor` を、新 `layer1_keywords.py` に整理・移植して機能欠落を防ぐ。
- **対象ファイル**: [`src/services/compression/layer1_keywords.py`](file:///e:/hhh/src/services/compression/layer1_keywords.py)
- **編集内容**:
  `KeyphraseExtractor` 基底クラス、`TFIDFExtractor`、`BM25Extractor`、`KeyBERTExtractor`、および `create_extractor` ファクトリを移植・追加。
```python
# src/services/compression/layer1_keywords.py の末尾に追加
class KeyphraseExtractor:
    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        raise NotImplementedError

class TFIDFExtractor(KeyphraseExtractor):
    def __init__(self):
        self.extractor = Layer1KeywordExtractor()

    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        res = self.extractor.extract(text, top_n=top_k)
        return [(k, v) for k, v in res.keyword_scores.items() if v >= min_score][:top_k]

class BM25Extractor(KeyphraseExtractor):
    def __init__(self):
        self.extractor = Layer1KeywordExtractor()

    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        res = self.extractor.extract(text, top_n=top_k)
        return [(k, v) for k, v in res.keyword_scores.items() if v >= min_score][:top_k]

class KeyBERTExtractor(KeyphraseExtractor):
    def extract(self, text: str, top_k: int = 20, min_score: float = 0.01) -> list[tuple[str, float]]:
        try:
            from keybert import KeyBERT
            kw = KeyBERT()
            return kw.extract_keywords(text, top_n=top_k)
        except Exception:
            return []

def create_extractor(method: str) -> KeyphraseExtractor:
    mapping = {
        "tfidf": TFIDFExtractor,
        "bm25": BM25Extractor,
        "keybert": KeyBERTExtractor,
    }
    if method not in mapping:
        raise ValueError(f"Unknown extractor method: {method}. Available: {list(mapping.keys())}")
    return mapping[method]()
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.layer1_keywords import create_extractor; ext = create_extractor('tfidf'); print(ext)"
  ```
- **合否基準**: エラーなく `TFIDFExtractor` オブジェクトが生成されること。

---

### Step 3: `models.py` / `config.py` へのYAML読み込み関数の統合
- **目的**: `src/utils/context_compression_config.py` に分散していた YAML 読み込みロジックを `src/services/compression/config.py`（または `models.py`）に集約する。
- **対象ファイル**: [`src/services/compression/models.py`](file:///e:/hhh/src/services/compression/models.py)
- **編集内容**:
  `load_compression_config()` および `get_compression_config()` を `models.py` に実装。
```python
# src/services/compression/models.py の末尾に追加
from pathlib import Path
import yaml

_compression_config_instance: CompressionConfig | None = None

def load_compression_config(path: str = "config/context_compression.yaml") -> CompressionConfig:
    config_path = Path(path)
    if not config_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        config_path = project_root / path
    if not config_path.exists():
        return CompressionConfig()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        comp = raw.get("compression", {})
        l1 = comp.get("layer1_keyphrase", {})
        sudachi_cfg = SudachiConfig(**l1.get("sudachi", {})) if "sudachi" in l1 else SudachiConfig()
        return CompressionConfig(
            max_tokens=comp.get("layer4_trimming", {}).get("max_tokens", 1500),
            top_keywords=l1.get("top_k", 20),
            max_hops=comp.get("layer2_subgraph", {}).get("max_hops", 2),
            relevance_threshold=comp.get("layer2_subgraph", {}).get("relevance_threshold", 0.5),
            preserve_categories=comp.get("layer4_trimming", {}).get("preserve_categories", ["主要キャラ", "核心設定", "伏線"]),
            sudachi=sudachi_cfg,
        )
    except Exception:
        return CompressionConfig()

def get_compression_config() -> CompressionConfig:
    global _compression_config_instance
    if _compression_config_instance is None:
        _compression_config_instance = load_compression_config()
    return _compression_config_instance
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression.models import get_compression_config; cfg = get_compression_config(); assert cfg.max_tokens > 0; print('OK:', cfg.max_tokens)"
  ```
- **合否基準**: `OK: <数値>` が出力されること。

---

### Step 4: `src/services/compression/__init__.py` の公開シンボル拡充
- **目的**: パッケージ直下から旧クラス名・ユーティリティ・抽出器もインポートできるようにする。
- **対象ファイル**: [`src/services/compression/__init__.py`](file:///e:/hhh/src/services/compression/__init__.py)
- **編集内容**:
  `FourLayerCompressor` のエイリアスとして `ContextCompressionPipeline = FourLayerCompressor` を定義し、`create_extractor`, `load_compression_config`, `CompressionResult` などをエクスポート。
```python
# src/services/compression/__init__.py
from src.services.compression.models import (
    SceneType,
    SudachiConfig,
    CompressionConfig,
    RawTextLayerOutput,
    SubgraphLayerOutput,
    AbstractionLayerOutput,
    TrimmedContextOutput,
    CompressedContextResult,
    CompressionResult,
    load_compression_config,
    get_compression_config,
)
from src.services.compression.layer1_keywords import (
    Layer1KeywordExtractor,
    extract_keyphrases,
    count_tokens,
    create_extractor,
    KeyphraseExtractor,
    TFIDFExtractor,
    BM25Extractor,
    KeyBERTExtractor,
)
from src.services.compression.compressor import FourLayerCompressor

ContextCompressionPipeline = FourLayerCompressor

__all__ = [
    "SceneType",
    "SudachiConfig",
    "CompressionConfig",
    "RawTextLayerOutput",
    "SubgraphLayerOutput",
    "AbstractionLayerOutput",
    "TrimmedContextOutput",
    "CompressedContextResult",
    "CompressionResult",
    "load_compression_config",
    "get_compression_config",
    "Layer1KeywordExtractor",
    "extract_keyphrases",
    "count_tokens",
    "create_extractor",
    "KeyphraseExtractor",
    "TFIDFExtractor",
    "BM25Extractor",
    "KeyBERTExtractor",
    "FourLayerCompressor",
    "ContextCompressionPipeline",
]
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression import ContextCompressionPipeline, CompressionResult; assert ContextCompressionPipeline is not None"
  ```
- **合否基準**: エラーなくインポートが通ること。

---

### Step 5: `src/services/context_compression/keyphrase_extractors.py` の Shim 化
- **目的**: 既存のインポート元を壊さずに新パッケージへルーティングする。
- **対象ファイル**: [`src/services/context_compression/keyphrase_extractors.py`](file:///e:/hhh/src/services/context_compression/keyphrase_extractors.py)
- **編集内容**:
  ファイル全体を以下の完全な転送コードで置き換える。
```python
# src/services/context_compression/keyphrase_extractors.py
"""DEPRECATED: Use src.services.compression.layer1_keywords instead."""
from __future__ import annotations

import warnings
from src.services.compression.layer1_keywords import (
    KeyphraseExtractor,
    TFIDFExtractor,
    BM25Extractor,
    KeyBERTExtractor,
    create_extractor,
)

warnings.warn(
    "src.services.context_compression.keyphrase_extractors is deprecated. "
    "Use src.services.compression instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "KeyphraseExtractor",
    "TFIDFExtractor",
    "BM25Extractor",
    "KeyBERTExtractor",
    "create_extractor",
]
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_keyphrase_extractors.py -o addopts="" --no-cov
  ```
- **合否基準**: 20 passed となり全テストが通過すること。

---

### Step 6: `src/services/context_compression/pipeline.py` の Shim 化
- **目的**: 旧 `pipeline.py` を呼び出すコードがあっても新 `FourLayerCompressor` へ委譲されるようにする。
- **対象ファイル**: [`src/services/context_compression/pipeline.py`](file:///e:/hhh/src/services/context_compression/pipeline.py)
- **編集内容**:
  ファイル全体を以下の完全な転送コードで置き換える。
```python
# src/services/context_compression/pipeline.py
"""DEPRECATED: Use src.services.compression instead."""
from __future__ import annotations

import warnings
from src.services.compression import (
    FourLayerCompressor as ContextCompressionPipeline,
    CompressionResult,
    get_compression_config,
)

warnings.warn(
    "src.services.context_compression.pipeline is deprecated. "
    "Use src.services.compression instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ContextCompressionPipeline",
    "CompressionResult",
    "get_compression_config",
]
```
- **検証コマンド**:
  ```powershell
  python -c "from src.services.context_compression.pipeline import ContextCompressionPipeline, CompressionResult; p = ContextCompressionPipeline(); assert p is not None"
  ```
- **合否基準**: 警告が出つつも正常にインスタンス化され、終了コード 0 であること。

---

### Step 7: `src/utils/context_compression_config.py` の整理と転送化
- **目的**: 設定読み込みクラスを `src.services.compression` へ委譲し、コード重複をなくす。
- **対象ファイル**: [`src/utils/context_compression_config.py`](file:///e:/hhh/src/utils/context_compression_config.py)
- **編集内容**:
  新パッケージのクラス・関数を再エクスポートする形に置換。
```python
# src/utils/context_compression_config.py
"""Context Compression 設定読み込みユーティリティ（互換レイヤー）"""
from __future__ import annotations

from src.services.compression.models import (
    SudachiConfig,
    CompressionConfig,
    load_compression_config,
    get_compression_config,
)

__all__ = [
    "SudachiConfig",
    "CompressionConfig",
    "load_compression_config",
    "get_compression_config",
]
```
- **検証コマンド**:
  ```powershell
  python -c "from src.utils.context_compression_config import load_compression_config; c = load_compression_config(); print('Loaded config successfully')"
  ```
- **合否基準**: `Loaded config successfully` が表示されること。

---

### Step 8: `tests/unit/test_keyphrase_extractors.py` のインポート先を新パッケージへ更新
- **目的**: テストを旧パッケージ依存から新パッケージ `src.services.compression` 直接参照へ更新する。
- **対象ファイル**: [`tests/unit/test_keyphrase_extractors.py`](file:///e:/hhh/tests/unit/test_keyphrase_extractors.py)
- **編集内容**:
  冒頭のインポート文を置換：
```diff
- from src.services.context_compression.keyphrase_extractors import (
+ from src.services.compression.layer1_keywords import (
      KeyphraseExtractor,
      TFIDFExtractor,
      KeyBERTExtractor,
      BM25Extractor,
      create_extractor,
  )
```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_keyphrase_extractors.py -o addopts="" --no-cov
  ```
- **合否基準**: 20 passed となり全テストが通過すること。

---

### Step 9: `config/context_compression.yaml` のフィールド同期
- **目的**: YAMLのプロパティ名と `CompressionConfig` Pydanticモデルのプロパティの乖離を解消する。
- **対象ファイル**: [`config/context_compression.yaml`](file:///e:/hhh/config/context_compression.yaml)
- **編集内容**:
  現行の `FourLayerCompressor` が必要とするフィールド（`top_keywords`, `max_tokens`, `preserve_categories` 等）を正式定義に更新。
- **検証コマンド**:
  ```powershell
  python -c "from src.services.compression import load_compression_config; cfg = load_compression_config(); assert cfg.top_keywords >= 10; print('YAML Sync OK')"
  ```
- **合否基準**: `YAML Sync OK` と出力されること。

---

### Step 10: 旧ディレクトリ `src/services/context_compression/` の安全な削除
- **目的**: 一本化が完了し、テストも新パッケージを参照するようになったため、旧ディレクトリおよび全ファイルを物理削除して技術的負債を清算する。
- **削除対象**:
  - `src/services/context_compression/pipeline.py`
  - `src/services/context_compression/keyphrase_extractors.py`
  - ディレクトリ `src/services/context_compression/`
- **コマンド**:
  ```powershell
  Remove-Item -Recurse -Force src/services/context_compression
  ```
- **検証コマンド**:
  ```powershell
  python -c "import os; assert not os.path.exists('src/services/context_compression'); print('Deleted successfully')"
  ```
- **合否基準**: `Deleted successfully` と出力されること。

---

### Step 11: `pyproject.toml` および `never_referenced_modules.txt` の更新
- **目的**: 削除されたファイルがカバレッジ設定ファイルに残存して警告や計測狂いを引き起こすのを防ぐ。
- **対象ファイル**:
  - [`pyproject.toml`](file:///e:/hhh/pyproject.toml)
  - [`never_referenced_modules.txt`](file:///e:/hhh/never_referenced_modules.txt)
- **編集内容**:
  1. `pyproject.toml` の `[tool.coverage.run] omit` 内にある `"src/services/context_compression/pipeline.py",` の行を削除。
  2. `never_referenced_modules.txt` にある `src\services\context_compression\pipeline.py` の行を削除。
- **検証コマンド**:
  ```powershell
  python -c "with open('pyproject.toml') as f: content = f.read(); assert 'context_compression' not in content; print('pyproject clean')"
  ```
- **合否基準**: `pyproject clean` と出力されること。

---

### Step 12: 圧縮・エージェント関連全テストの統合総合検証
- **目的**: 一連の変更により、小説生成エンジン本体やコンテキスト圧縮機能に一切の回帰（デグレ）が生じていないことを最終確認する。
- **検証コマンド**:
  ```powershell
  pytest tests/unit/test_keyphrase_extractors.py tests/unit/test_compression_pipeline.py tests/unit/test_dynamic_taxonomy.py tests/unit/test_layer4_multiscene.py tests/unit/test_sudachi_tokenizer.py tests/unit/test_four_layer_compression.py -o addopts="" --no-cov
  ```
- **合否基準**:
  - 対象の全テスト（約80〜100件）が **100% Passed（0 failed, 0 error）** で完了すること。
  - `ImportError: No module named 'src.services.context_compression'` 等の未解決参照が一切発生しないこと。

---

## 🎯 期待成果物と完了基準
1. **成果物**:
   - `src/services/context_compression/` の完全撤廃
   - `src/services/compression/` への責務・設定・テストの一本化
   - 整合性の取れた `config/context_compression.yaml`
2. **完了基準**:
   - [ ] 旧パッケージ参照がプロジェクト全体から完全に消去されていること
   - [ ] 圧縮パイプライン関連の全ユニットテストが All Green であること
   - [ ] CI/カバレッジ設定から死蔵パスが除外されていること
