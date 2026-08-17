# 48ステップ実装計画のステップ20を実行

## ステップ20: 現状把握 - `spice_guard.py` の分割ポイント調査
### 元の目的: パターン定義・抽出・マーカー操作の責務分離

## 実装ログ

### ステップ20-1: 対象ファイルを開く
✅ `/home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` を開いた
✅ ファイルが正常に開けること
📄 ファイル内容: 537行のSpiceGuard実装

### ステップ20-2: ファイルの全体構造を理解する
✅ ファイルの先頭から最後までざっと読んだ
📊 全体構造:
- インポートブロック (lines 1-12)
- SpiceElement データクラス (lines 14-23)
- SpiceGuard クラス (lines 25-537)
  - UNIVERSAL_PATTERNS 定数 (lines 29-59)
  - GENRE_PATTERNS 定数 (lines 61-150)
  - 各種メソッド (抽出、マーカー操作、プロンプト構築など)

### ステップ20-3: クラス定義を特定する
✅ `class SpiceElement` (line 14)
✅ `class SpiceGuard` (line 25)

### ステップ20-4: メソッド定義を特定する
✅ 抽出メソッドらしきもの: `extract_spice` (線形検索で見つける必要がある)
✅ マーカー操作メソッドらしきもの: `inject_markers`, `remove_markers` など
✅ プロンプト構築メソッドらしきもの: `build_prompt`, `build_rewrite_prompt` など
🔍 詳細: `grep -n "def " /home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` を実行

### ステップ20-5: 定数定義を特定する
✅ `UNIVERSAL_PATTERNS` (line 29)
✅ `GENRE_PATTERNS` (line 61)

### ステップ20-6: UNIVERSAL_PATTERNS の詳細を確認する
✅ UNIVERSAL_PATTERNS 定数を確認
📋 内容:
- "unique_metaphor": パターンリスト + priority: "high"
- "plot_twist_marker": キーワードリスト + priority: "critical"
- "emotional_raw": パターンリスト + priority: "high"

### ステップ20-7: GENRE_PATTERNS の詳細を確認する
✅ GENRE_PATTERNS 定数を確認
📋 内容:
- "zarma": catharsis_payoff, villain_despair, power_gap など
- "aku_reijo": flag_avoidance, yuri_tension など
- "cheat_tensei": system_flavor, efficiency_brag など
- （他にも多くのジャンルが定義されている）

### ステップ20-8: SpiceGuard クラスのメソッドを列挙する
✅ SpiceGuard クラス内のメソッドをリストアップ
📋 主なメソッド:
- `__init__`
- `extract_spice` (抽出ロジック)
- `inject_markers` (マーカー注入)
- `remove_markers` (マーカー除去)
- `build_prompt` (プロンプト構築)
- `build_rewrite_prompt` (リライトプロンプト構築)
- （その他にもいくつかのヘルパーメソッド）

### ステップ20-9: 各メソッドの責務を分類する準備をする
✅ 各メソッドの責務を分類:
- 抽出ロジック: `extract_spice`
- マーカー操作: `inject_markers`, `remove_markers`
- プロンプト構築: `build_prompt`, `build_rewrite_prompt`
- パターン定義: `UNIVERSAL_PATTERNS`, `GENRE_PATTERNS` (定数として)

### ステップ20-10: SpiceElement データクラスを確認する
✅ SpiceElement データクラスを確認
📋 内容:
- `type`: str (スパイスの種類)
- `text`: str (元のテキスト)
- `position`: int (文字位置)
- `priority`: str (優先度)
- `metadata`: Dict = field(default_factory=dict)

### ステップ20-11: メソッドの複雑度を推定する
✅ 各メソッドの複雑度を推定
📊 抽出ロジック (`extract_spice`): 最も複雑（ネストしたループと条件分岐）
📊 マーカー操作: 中程度の複雑度
📊 プロンプト構築: 比較的簡単
📊 パターン定義: 定数なので複雑度なし

### ステップ20-12: 外部依存を確認する
✅ 外部依存を確認
📋 インポート:
- `from __future__ import annotations`
- `import re`
- `from dataclasses import dataclass, field`
- `from typing import Dict, List, Set`
- `from src.presets.loader import load_preset`
🎯 外部依存: `src.presets.loader.load_preset` のみ

### ステップ20-13: 分割の観点を整理する
✅ 分割の観点を整理
🎯 4つの責務に分けることが適切:
1. パターン定義 (UNIVERSAL_PATTERNS, GENRE_PATTERNS)
2. 抽出ロジック (SpiceElement の抽出)
3. マーカー操作 (注入・除去)
4. プロンプト構築 (リライトプロンプト構築)

### ステップ20-14: 分割設計図の構想を始める
✅ 分割設計図の構想を始めた
🎯 構想:
```
src/easy_mode/spice_guard/
  pattern_registry.py     # パターン定義（UNIVERSAL_PATTERNS, GENRE_PATTERNS）
  extractor.py            # 抽出ロジック（SpiceElement の抽出）
  marker.py               # マーカー操作（注入・除去）
  prompt_builder.py       # リライトプロンプト構築
  spice_guard.py          # ファサード・オーケストレーション専用（後方互換）
```

### ステップ20-15: 分割設計図ファイルの準備をする
✅ 出力先のファイルパスを確認した
✅ `/home/herbmatsui/autonovel/proposals/spice_guard_split_design.md` が存在しないことを確認
✅ 新規作成する準備をした

### ステップ20-16: 分割設計図にヘッダーを書く
✅ ファイルにヘッダー情報を書き込んだ
📄 内容:
```
# SpiceGuard 分割設計図
作成日: 2026-08-17
```

### ステップ20-17: 分割設計図にモジュール構造を書く
✅ 分割設計図にモジュール構造を書き込んだ
📄 内容:
```
## 提案されるモジュール構造

src/easy_mode/spice_guard/
  pattern_registry.py     # パターン定義（UNIVERSAL_PATTERNS, GENRE_PATTERNS）
  extractor.py            # 抽出ロジック（SpiceElement の抽出）
  marker.py               # マーカー操作（注入・除去）
  prompt_builder.py       # リライトプロンプト構築
  spice_guard.py          # ファサード・オーケストレーション専用（後方互換）
```

### ステップ20-18: 各モジュールの責務を説明する
✅ 各モジュールの責務を説明した
📋 説明内容を追加:
- pattern_registry.py: パターン定義データを一元管理
- extractor.py: テキストから SpiceElement オブジェクトを抽出
- marker.py: SpiceElement に基づいてマーカーを注入・除去
- prompt_builder.py: リライト用のプロンプトを構築
- spice_guard.py: 上記モジュールをオーケストレーションし、後方互換性を維持

### ステップ20-19: インターフェースを検討する
✅ インターフェースを検討した
🔗 インターフェース設計:
- pattern_registry.py: UNIVERSAL_PATTERNS, GENRE_PATTERNS としてデータをエクスポート
- extractor.py: SpiceExtractor クラスに `extract(text: str) -> List[SpiceElement]` メソッド
- marker.py: SpiceMarkerInjector クラスに `inject(text: str, elements: List[SpiceElement]) -> str` メソッド
  - SpiceMarkerCleaner クラスに `clean(text: str) -> str` メソッド
- prompt_builder.py: PromptBuilder クラスに `build_prompt(...)` と `build_rewrite_prompt(...)` メソッド
- spice_guard.py: これらのクラスをオーケストレーションするファサード

### ステップ20-20: 設計図の内容を確認する
✅ 作成したファイルの内容を読み返した
📄 `/home/herbmatsui/autonovel/proposals/spice_guard_split_design.md` の内容を確認
✅ 必要な情報がすべて含まれていること
🎯 調査目的が達成されていること

### ステップ20-21: 作業の完了を宣言する
✅ ステップ20のすべてのマイクロステップが完了したことを記録する
✅ 次のステップに進む準備ができていること