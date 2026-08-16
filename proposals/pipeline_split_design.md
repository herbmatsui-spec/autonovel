# `pipeline.py` 分割設計書

作成日: 2026-08-16
対象: `src/easy_mode/pipeline.py` (633行 → 200行以下目標)

---

## 1. 現状のメソッド分類

### パイプライン主要ステップ（抽出対象）

| # | メソッド | 行数 | 責務 | 依存 |
|---|---------|------|------|------|
| 1 | `_generate_bible` | 42 | Bible生成・パース・フォールバック | engine.llm, preset |
| 2 | `_generate_plot_outline` | 33 | プロット生成・テンション補間・パターン選択 | preset, config |
| 3 | `_generate_episode` | 56 | エピソード生成オーケストレーション（執筆→監査→リライト） | engine, _write_episode, _audit_episode, _rewrite_episode |
| 4 | `_write_episode` | 20 | 執筆プロンプト構築・LLM呼び出し | engine.llm, preset |
| 5 | `_build_writing_prompt` | 34 | 執筆プロンプトテンプレート | - |
| 6 | `_audit_episode` | 34 | 監査エージェント呼び出し・スコア正規化 | engine.auditor |
| 7 | `_extract_spice` | 5 | SpiceGuard抽出ラッパー | spice_guard |
| 8 | `_inject_spice_markers` | 17 | マーカー注入 | - |
| 9 | `_rewrite_episode` | 32 | リライトプロンプト構築・LLM呼び出し・マーカー除去 | engine.llm, _inject_spice_markers |
| 10 | `_build_rewrite_prompt` | 7 | リライトプロンプト構築（テスト用） | spice_guard |
| 11 | `_finalize_series` | 25 | 完結処理・メタデータ生成 | preset |

### ヘルパーメソッド（抽出対象・共通ユーティリティ）

| メソッド | 行数 | 責務 | 依存 |
|---------|------|------|------|
| `_get_preset_defaults` | 32 | プリセットからデフォルト値抽出 | preset |
| `_parse_bible` | 10 | Bibleテキスト→辞書 | json |
| `_fallback_bible` | 10 | フォールバックBible構築 | - |
| `_interpolate_tension` | 13 | テンション曲線補間 | - |
| `_select_plot_pattern` | 46 | プロットパターン選択 | config.constants |
| `_build_prev_context` | 10 | 前話要約構築 | - |
| `_report_progress` | 4 | 進捗コールバック | config |

---

## 2. 新ディレクトリ構造

```
src/easy_mode/
├── pipeline.py              # オーケストレーション専用（~200行）
├── bible_generator.py       # Bible生成モジュール
├── plot_generator.py        # プロット生成モジュール
├── episode_writer.py        # エピソード執筆モジュール
├── episode_auditor.py       # エピソード監査モジュール
├── episode_rewriter.py      # エピソードリライトモジュール
├── series_finalizer.py      # シリーズ完結モジュール
├── progress_reporter.py     # 進捗報告ユーティリティ
├── presets/
│   └── loader.py            # 既存
├── spice_guard/
│   ├── __init__.py
│   ├── pattern_registry.py  # パターン定義
│   ├── extractor.py         # 抽出
│   └── marker.py            # マーカー注入・除去
└── models.py                # 共通データクラス（EpisodeResult, SeriesResult, PipelineConfig）
```

---

## 3. 各モジュールの公開API設計

### 3.1 `models.py` - 共通データクラス
```python
@dataclass
class EpisodeResult:
    episode_num: int
    title: str
    content: str
    word_count: int
    audit_score: float
    audit_passed: bool
    rewrite_count: int
    spice_elements: List[SpiceElement]
    metadata: Dict[str, Any]
    needs_human_review: bool = False

@dataclass
class SeriesResult:
    genre: str
    title: str
    concept: str
    total_episodes: int
    episodes: List[EpisodeResult]
    bible: Dict[str, Any]
    plot_outline: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "completed"

@dataclass
class PipelineConfig:
    genre: str
    target_episodes: int = 8
    max_rewrite_iterations: int = 3
    target_audit_score: float = 95.0
    enable_spice_guard: bool = True
    progress_callback: Optional[Callable[[str, int, int], None]] = None
```

### 3.2 `bible_generator.py`
```python
class BibleGenerator:
    def __init__(self, preset: Dict[str, Any], engine_llm, retry_config: RetryConfig):
        ...
    
    async def generate(self, target_episodes: int) -> Dict[str, Any]:
        """Bible生成メインエントリ"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Bibleテキストパース"""
    
    def fallback(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """フォールバック生成"""
```

### 3.3 `plot_generator.py`
```python
class PlotGenerator:
    def __init__(self, preset: Dict[str, Any], target_episodes: int):
        ...
    
    async def generate(self, bible: Dict[str, Any]) -> List[Dict[str, Any]]:
        """プロットアウトライン生成"""
    
    def interpolate_tension(self, progress: float, curve_points: List) -> float:
        """テンション補間"""
    
    def select_pattern(self, ep_num: int, is_catharsis: bool) -> Dict:
        """パターン選択"""
```

### 3.4 `episode_writer.py`
```python
class EpisodeWriter:
    def __init__(self, engine_llm, preset: Dict[str, Any], retry_config: RetryConfig):
        ...
    
    async def write(self, ep_num: int, bible: Dict, plot: Dict, prev_context: str) -> str:
        """エピソード執筆"""
    
    def build_prompt(self, ep_num: int, bible: Dict, plot: Dict, prev_context: str,
                     style_dna: Dict, hooks: Dict, erotic_rules: Dict) -> str:
        """プロンプト構築"""
```

### 3.5 `episode_auditor.py`
```python
class EpisodeAuditor:
    def __init__(self, engine_auditor, target_audit_score: float):
        ...
    
    async def audit(self, content: str, bible: Dict, plot: Dict, ep_num: int, genre: str) -> AuditResult:
        """監査実行・スコア正規化"""
```

### 3.6 `episode_rewriter.py`
```python
class EpisodeRewriter:
    def __init__(self, engine_llm, spice_guard, retry_config: RetryConfig):
        ...
    
    async def rewrite(self, content: str, improvements: List[str], 
                      spice_elements: List[SpiceElement]) -> str:
        """SpiceGuard付きリライト"""
    
    def inject_markers(self, text: str, elements: List[SpiceElement]) -> str:
        """マーカー注入"""
    
    def clean_markers(self, text: str) -> str:
        """マーカー除去"""
    
    def build_prompt(self, content: str, improvements: List[str], 
                     elements: List[SpiceElement]) -> str:
        """リライトプロンプト構築"""
```

### 3.7 `series_finalizer.py`
```python
class SeriesFinalizer:
    def __init__(self, preset: Dict[str, Any]):
        ...
    
    async def finalize(self, bible: Dict, plot_outline: List, 
                       episodes: List[EpisodeResult]) -> Dict:
        """完結処理・メタデータ生成"""
```

### 3.8 `progress_reporter.py`
```python
def create_progress_reporter(callback: Optional[Callable]) -> ProgressReporter:
    """進捗報告ファクトリ"""
    
class ProgressReporter:
    async def report(self, stage: str, current: int, total: int):
        ...
```

---

## 4. 依存関係図

```
EasyModePipeline (orchestrator)
├── BibleGenerator
│   └── engine.llm, retry_config
├── PlotGenerator
│   └── preset, config
├── EpisodeWriter
│   └── engine.llm, preset, retry_config
├── EpisodeAuditor
│   └── engine.auditor, target_audit_score
├── EpisodeRewriter
│   └── engine.llm, spice_guard, retry_config
├── SeriesFinalizer
│   └── preset
└── ProgressReporter
    └── config.progress_callback

RetryConfig: MAX_LLM_RETRIES, LLM_RETRY_DELAY (クラス定数から移動)
```

---

## 5. 移行手順

### Phase A: 共通基盤
1. `models.py` 作成（データクラス移動）
2. `RetryConfig` クラス作成

### Phase B: 生成系モジュール
3. `bible_generator.py` 作成・テスト
4. `plot_generator.py` 作成・テスト

### Phase C: エピソード処理系
5. `episode_writer.py` 作成・テスト
6. `episode_auditor.py` 作成・テスト
7. `episode_rewriter.py` 作成・テスト

### Phase D: 完結・進行
8. `series_finalizer.py` 作成・テスト
9. `progress_reporter.py` 作成・テスト

### Phase E: オーケストレーション
10. `pipeline.py` 全面書き換え（各モジュールをDIで受け取りrun()で連携）
11. 既存テスト全パス確認

---

## 6. 完了基準

- [ ] `pipeline.py` が 200 行以下
- [ ] 各モジュールが単体テスト可能
- [ ] `tests/test_phase2_pipeline_integration.py` 全パス
- [ ] `mypy --strict` エラー増加なし
- [ ] 循環インポートなし