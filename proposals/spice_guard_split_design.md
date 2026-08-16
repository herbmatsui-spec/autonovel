# `spice_guard.py` 分割設計書

作成日: 2026-08-16
対象: `src/easy_mode/spice_guard.py` (537行 → 各モジュール 150-200行)

---

## 1. 現状のクラス・メソッド分類

### SpiceElement (データクラス)
- 共通データクラス、分割不要

### SpiceGuard クラスの責務分解

| 責務 | メソッド | 行数 | 依存 |
|------|---------|------|------|
| **パターン定義** | `UNIVERSAL_PATTERNS`, `GENRE_PATTERNS`, `_compile_patterns` | ~340 | re, load_preset |
| **抽出** | `extract_spice`, `_extract_character_elements`, `_deduplicate_and_sort` | ~70 | パターン定義 |
| **マーカー操作** | `inject_markers`, `remove_markers`, `clean_output` | ~20 | re |
| **プロンプト構築** | `build_rewrite_prompt` | ~20 | マーカー操作 |
| **ファサード** | `create_spice_guard` | ~5 | - |

---

## 2. 新ディレクトリ構造

```
src/easy_mode/spice_guard/
├── __init__.py              # ファサード（既存API維持）
├── pattern_registry.py      # パターン定義・コンパイル
├── extractor.py             # 抽出ロジック
└── marker.py                # マーカー注入・除去・プロンプト構築
```

---

## 3. 各モジュールの公開API設計

### 3.1 `pattern_registry.py` - パターン定義・コンパイル
```python
# パターン定義（定数）
UNIVERSAL_PATTERNS = {...}
GENRE_PATTERNS = {...}

class CompiledPatternCache:
    """正規表現コンパイル結果のキャッシュ"""
    def __init__(self):
        self._cache: Dict[str, List[re.Pattern]] = {}
    
    def get(self, genre: str) -> Dict[str, List[re.Pattern]]:
        if genre not in self._cache:
            self._cache[genre] = self._compile_for_genre(genre)
        return self._cache[genre]
    
    def _compile_for_genre(self, genre: str) -> Dict[str, List[re.Pattern]]:
        # 普遍 + ジャンル別パターンをコンパイル

# グローバルキャッシュインスタンス
pattern_cache = CompiledPatternCache()

def get_compiled_patterns(genre: str) -> Dict[str, List[re.Pattern]]:
    return pattern_cache.get(genre)

def get_universal_patterns() -> Dict:
    return UNIVERSAL_PATTERNS

def get_genre_patterns(genre: str) -> Dict:
    return GENRE_PATTERNS.get(genre, {})
```

### 3.2 `extractor.py` - 抽出ロジック
```python
class SpiceExtractor:
    def __init__(self, genre: str):
        self.genre = genre
        self.compiled_patterns = get_compiled_patterns(genre)
        self.universal_patterns = get_universal_patterns()
        self.genre_patterns = get_genre_patterns(genre)
        self.preset = load_preset(genre)
    
    def extract(self, text: str) -> List[SpiceElement]:
        elements = []
        # 1. 普遍パターン
        elements.extend(self._extract_universal(text))
        # 2. ジャンル別パターン
        elements.extend(self._extract_genre(text))
        # 3. キャラクター固有
        elements.extend(self._extract_character(text))
        # 4. 重複除去・ソート
        return self._deduplicate_and_sort(elements)
    
    def _extract_universal(self, text: str) -> List[SpiceElement]: ...
    def _extract_genre(self, text: str) -> List[SpiceElement]: ...
    def _extract_character(self, text: str) -> List[SpiceElement]: ...
    def _deduplicate_and_sort(self, elements: List[SpiceElement]) -> List[SpiceElement]: ...
```

### 3.3 `marker.py` - マーカー操作・プロンプト構築
```python
class SpiceMarkerInjector:
    def inject(self, text: str, elements: List[SpiceElement]) -> str:
        # マーカー注入
    
    def remove(self, text: str) -> str:
        # マーカー除去
    
    def clean_output(self, text: str) -> str:
        return self.remove(text)

class RewritePromptBuilder:
    def __init__(self, marker_injector: SpiceMarkerInjector):
        self.marker_injector = marker_injector
    
    def build(self, content: str, improvements: List[str], elements: List[SpiceElement]) -> str:
        protected = self.marker_injector.inject(content, elements)
        # プロンプト構築
        return prompt
```

### 3.4 `__init__.py` - ファサード（後方互換）
```python
from .pattern_registry import UNIVERSAL_PATTERNS, GENRE_PATTERNS
from .extractor import SpiceExtractor
from .marker import SpiceMarkerInjector, RewritePromptBuilder

class SpiceGuard:
    """後方互換ファサード"""
    def __init__(self, genre: str):
        self.genre = genre
        self.extractor = SpiceExtractor(genre)
        self.marker = SpiceMarkerInjector()
        self.prompt_builder = RewritePromptBuilder(self.marker)
    
    def extract_spice(self, text: str) -> List[SpiceElement]:
        return self.extractor.extract(text)
    
    def inject_markers(self, text: str, elements: List[SpiceElement]) -> str:
        return self.marker.inject(text, elements)
    
    def remove_markers(self, text: str) -> str:
        return self.marker.remove(text)
    
    def build_rewrite_prompt(self, content: str, improvements: List[str], elements: List[SpiceElement]) -> str:
        return self.prompt_builder.build(content, improvements, elements)
    
    def clean_output(self, text: str) -> str:
        return self.marker.clean_output(text)

# 既存API維持
def create_spice_guard(genre: str) -> SpiceGuard:
    return SpiceGuard(genre)

__all__ = [
    "SpiceElement",
    "SpiceGuard",
    "create_spice_guard",
    "SpiceExtractor",
    "SpiceMarkerInjector",
    "RewritePromptBuilder",
]
```

---

## 4. 依存関係図

```
SpiceGuard (facade)
├── SpiceExtractor
│   ├── CompiledPatternCache (from pattern_registry)
│   ├── UNIVERSAL_PATTERNS (from pattern_registry)
│   ├── GENRE_PATTERNS (from pattern_registry)
│   └── load_preset
├── SpiceMarkerInjector
│   └── re
└── RewritePromptBuilder
    └── SpiceMarkerInjector
```

---

## 5. 移行手順

1. `src/easy_mode/spice_guard/` ディレクトリ作成
2. `pattern_registry.py` 作成（パターン定義移動）
3. `extractor.py` 作成（抽出ロジック移動）
4. `marker.py` 作成（マーカー・プロンプト移動）
5. `__init__.py` 作成（ファサード）
6. 既存 `spice_guard.py` を薄いラッパーにするか削除
7. 既存テスト `tests/test_sharp_edge_preserver.py` 等で動作確認

---

## 6. 完了基準

- [ ] 元の `spice_guard.py` が 3 ファイルに分割
- [ ] `SpiceGuard` クラスの既存APIが維持される
- [ ] `tests/test_phase2_pipeline_integration.py` の SpiceGuard テスト全パス
- [ ] `tests/test_sharp_edge_preserver.py` 全パス
- [ ] 各モジュールが単体テスト可能