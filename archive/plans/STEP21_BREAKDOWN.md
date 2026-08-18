# 48ステップ実装計画のステップ21をさらに小さなステップに分解

## ステップ21: 実装 - `spice_guard/pattern_registry.py` の抽出
### 元の目的: パターン定義を一元管理する

### さらに細分化されたサブステップ（各ステップ3-5分で完了）

#### ステップ21-1: 対象ディレクトリを確認する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/` ディレクトリの内容を確認する
- **確認**: ディレクトリが存在し、既に一部のファイルが作成されていること
- **ツール**: `ls -la /home/herbmatsui/autonovel/src/easy_mode/spice_guard/`

#### ステップ21-2: 既存の pattern_registry.py を確認する（ある場合）
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/pattern_registry.py` が存在するか確認する
- **確認**: 存在する場合は内容を確認し、どこまで実装されているか判断する
- **ツール**: `ls /home/herbmatsui/autonovel/src/easy_mode/spice_guard/pattern_registry.py`

#### ステップ21-3: pattern_registry.py が存在しない場合は新規作成する準備をする
- **アクション**: ファイルが存在しない場合は、新規作成する準備をする
- **確認**: 新規作成することを決定する
- **判定**: 新規作成するか、既存ファイルを更新するかを決定する

#### ステップ21-4: SpiceGuard.py から UNIVERSAL_PATTERNS をコピーする準備をする
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` から UNIVERSAL_PATTERNS の定義をコピーする準備をする
- **確認**: コピーする内容を特定する
- **作業内容**: UNIVERSAL_PATTERNS 辞書の定義を特定する

#### ステップ21-5: SpiceGuard.py から GENRE_PATTERNS をコピーする準備をする
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` から GENRE_PATTERNS の定義をコピーする準備をする
- **確認**: コピーする内容を特定する
- **作業内容**: GENRE_PATTERNS 辞書の定義を特定する

#### ステップ21-6: CompiledPatternCache クラスの構想を始める
- **アクション**: 正規表現の事前コンパイルを効率的に行うクラスを考える
- **確認**: どのようにキャッシュを実装するかを考える
- **作業内容**の例:
  ```python
  class CompiledPatternCache:
      def __init__(self):
          self._universal_cache = {}
          self._genre_cache = {}
      
      def get_universal_pattern(self, pattern_key: str) -> Pattern:
          # キャッシュから取得またはコンパイルしてキャッシュ
          pass
          
      def get_genre_pattern(self, genre: str, pattern_key: str) -> Pattern:
          # キャッシュから取得またはコンパイルしてキャッシュ
          pass
  ```

#### スteps21-7: pattern_registry.py のファイル構造を作成する
- **アクション**: 新しい pattern_registry.py ファイルの基本構造を作成する
- **確認**: ファイルが正常に作成できること
- **作業内容**の例:
  ```python
  """
  SpiceGuard パターンレジストリ
  """
  from __future__ import annotations
  
  import re
  from typing import Dict, List, Pattern
  
  # ここにパターン定義を配置
  
  
  class CompiledPatternCache:
      """正規表現の事前コンパイルキャッシュ"""
      pass
  ```

#### ステップ21-8: pattern_registry.py を作成する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/pattern_registry.py` を作成する
- **確認**: ファイルが正常に作成されること
- **ツール**: `write` ツールを使ってファイルを作成する

#### ステップ21-9: UNIVERSAL_PATTERNS を pattern_registry.py に移植する
- **アクション**: ステップ21-4 で特定した UNIVERSAL_PATTERNS を pattern_registry.py に書き込む
- **確認**: ファイルに正しくコピーされていること
- **ツール**: `edit` ツールを使ってファイルに書き込む

#### ステップ21-10: GENRE_PATTERNS を pattern_registry.py に移植する
- **アクション**: ステップ21-5 で特定した GENRE_PATTERNS を pattern_registry.py に書き込む
- **確認**: ファイルに正しくコピーされていること
- **ツール**: `edit` ツールを使ってファイルに書き込む

#### ステップ21-11: CompiledPatternCache クラスを実装する
- **アクション**: ステップ21-6 で構想した CompiledPatternCache クラスを実装する
- **確認**: クラスが正しく実装されていること
- **作業内容**の例:
  ```python
  class CompiledPatternCache:
      """正規表現の事前コンパイルキャッシュ"""
      
      def __init__(self):
          self._universal_cache: Dict[str, Pattern] = {}
          self._genre_cache: Dict[str, Dict[str, Pattern]] = {}
      
      def get_universal_pattern(self, pattern_key: str) -> Pattern:
          if pattern_key not in self._universal_cache:
              pattern_str = UNIVERSAL_PATTERNS[pattern_key]["pattern"]
              self._universal_cache[pattern_key] = re.compile(pattern_str)
          return self._universal_cache[pattern_key]
      
      def get_genre_pattern(self, genre: str, pattern_key: str) -> Pattern:
          if genre not in self._genre_cache:
              self._genre_cache[genre] = {}
          if pattern_key not in self._genre_cache[genre]:
              pattern_str = GENRE_PATTERNS[genre][pattern_key]["pattern"]
              self._genre_cache[genre][pattern_key] = re.compile(pattern_str)
          return self._genre_cache[genre][pattern_key]
  ```

#### ステップ21-12: UNIVERSAL_PATTERNS と GENRE_PATTERNS を適切な形式に変換する
- **アクション**: コピーした UNIVERSAL_PATTERNS と GENRE_PATTERNS を、CompiledPatternCache が使いやすい形式に調整する
- **確認**: 必要ならデータ構造を変換する
- **判定**: 元の形式を保持するか、アクセスしやすい形式に変換するかを決める

#### ステップ21-13: パターンへのアクセス方法を提供する関数を追加する
- **アクション**: 外部からパターンにアクセスできるように、関数を追加する準備をする
- **確認**: どのようなインターフェースを提供するかを考える
- **作業内容**の例:
  ```python
  def get_universal_patterns() -> Dict[str, Dict]:
      """UNIVERSAL_PATTERNS のコピーを返す"""
      return UNIVERSAL_PATTERNS.copy()
  
  def get_genre_patterns() -> Dict[str, Dict]:
      """GENRE_PATTERNS のコピーを返す"""
      return GENRE_PATTERNS.copy()
  ```

#### ステップ21-14: 変更後のファイルを読んで確認する
- **アクション**: 作成した `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/pattern_registry.py` を読む
- **確認**: UNIVERSAL_PATTERNS、GENRE_PATTERNS、CompiledPatternCache が正しく含まれていること
- **判定**: ファイルが正しく作成されているか確する

#### ステップ21-15: 元の spice_guard.py から UNIVERSAL_PATTERNS と GENRE_PATTERNS を削除する準備をする
- **アクション**: 元のファイルからコピーした定数を削除する準備をする
- **確認**: 削除する範囲を特定する
- **作業内容**: UNIVERSAL_PATTERNS と GENRE_PATTERNS の定義範囲を特定する

#### ステップ21-16: 元の spice_guard.py から UNIVERSAL_PATTERNS を削除する
- **アクション**: 特定した UNIVERSAL_PATTERNS の定義範囲を、空白またはコメントに置換する
- **確認**: 削除が正しく行われたこと
- **ツール**: `edit` ツールを使って置換する

#### ステップ21-17: 元の spice_guard.py から GENRE_PATTERNS を削除する
- **アクション**: 特定した GENRE_PATTERNS の定義範囲を、空白またはコメントに置換する
- **確認**: 削除が正しく行われたこと
- **ツール**: `edit` ツールを使って置換する

#### ステップ21-18: 元の spice_guard.py に pattern_registry.py からのインポートを追加する
- **アクション**: 元のファイルの上部に、pattern_registry から必要なものをインポートするコードを追加する準備をする
- **確認**: インポート文が正しく追加されること
- **作業内容**の例:
  ```python
  from .pattern_registry import UNIVERSAL_PATTERNS, GENRE_PATTERNS, CompiledPatternCache
  ```

#### ステップ21-19: 元の spice_guard.py のインポートを追加する
- **アクション**: 元のファイルの上部のインポートブロックに、ステップ21-18 で準備したインポート文を追加する
- **確認**: インポートが正しく追加されていること
- **ツール**: `edit` ツールを使ってインポートブロックに追加する

#### ステップ21-20: 元の spice_guard.py で UNIVERSAL_PATTERNS と GENRE_PATTERNS を参照している場所を更新する
- **アクション**: 元のファイル内で UNIVERSAL_PATTERNS と GENRE_PATTERNS を参照している場所を、新しいインポート先を参照するように変更する
- **確認**: 参照が正しく更新されていること
- **作業内容**: `UNIVERSAL_PATTERNS` をそのまま参照すれば良い（インポート名が同じ場合）

#### ステップ21-21: 変更後の spice_guard.py を読んで確認する
- **アクション**: 変更後の `/home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` を読む
- **確認**: UNIVERSAL_PATTERNS と GENRE_PATTERNS がインポートされていること
- **確認**: 元の定義が削除されていること
- **判定**: 変更が正しく行われているか確認する

#### ステップ21-22: pattern_registry.py の構文を確認する
- **アクション**: `python -m py_compile /home/herbmatsui/autonovel/src/easy_mode/spice_guard/pattern_registry.py` を実行する
- **確認**: エラーが出ないこと
- **判定**: 構文エラーがないか確認する

#### ステップ21-23: spice_guard.py の構文を確認する
- **アクション**: `python -m py_compile /home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` を実行する
- **確認**: エラーが出ないこと
- **判定**: 構文エラーがないか確認する

#### ステップ21-24: 単体テストを作成する準備をする
- **アクション**: pattern_registry.py の機能をテストする単体テストを作成する準備をする
- **確認**: テストファイルを作成できること
- **判定**: どのようなテストを行うかを考える

#### ステップ21-25: pattern_registry.py の単体テストファイルを作成する
- **アクション**: `/home/herbmatsui/autonovel/tests/unit/test_spice_guard_pattern_registry.py` を作成する
- **確認**: ファイルが正常に作成されること
- **ツール**: `write` ツールを使ってファイルを作成する

#### ステップ21-26: 基本的なテストを実装する
- **アクション**: pattern_registry.py が正しくインポートできることと、基本的な機能が動作することをテストする
- **確認**: テストがパスすること
- **作業内容**の例:
  ```python
  from src.easy_mode.spice_guard.pattern_registry import (
      UNIVERSAL_PATTERNS, 
      GENRE_PATTERNS, 
      CompiledPatternCache
  )
  
  def test_pattern_registry_import():
      """基本的なインポートテスト"""
      assert UNIVERSAL_PATTERNS is not None
      assert GENRE_PATTERNS is not None
      cache = CompiledPatternCache()
      assert cache is not None
  
  def test_universal_patterns_access():
      """UNIVERSAL_PATTERNS へのアクセステスト"""
      assert "unique_metaphor" in UNIVERSAL_PATTERNS
      assert "plot_twist_marker" in UNIVERSAL_PATTERNS
  
  def test_genre_patterns_access():
      """GENRE_PATTERNS へのアクセステスト"""
      assert "zarma" in GENRE_PATTERNS
      assert "aku_reijo" in GENRE_PATTERNS
  ```

#### ステップ21-26: 単体テストを実行する
- **アクション**: 作成した単体テストを実行する
- **確認**: テストがパスすること
- **判定**: 基本的な機能が正しく動作することを確認する
- **ツール**: `python -m pytest /home/herbmatsui/autonovel/tests/unit/test_spice_guard_pattern_registry.py -v`

#### ステップ21-27: パターンマッチング速度のベンチマークを実行する準備をする
- **アクション**: パターンマッチング速度が20%以上向上したかを測定する準備をする
- **確認**: ベンチマークを実行できるスクリプトを作成できること
- **判定**: 何を測定するかを考える（たとえば、特定のテキストに対するマッチング時間など）

#### ステップ21-28: 作業の完了を宣言する
- **アクション**: ステップ21のすべてのマイクロステップが完了したことを記録する
- **確認**: 次のステップに進む準備ができていること

## 完了基準
- [ ] `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/pattern_registry.py` が作成されている
- [ ] UNIVERSAL_PATTERNS と GENRE_PATTERNS が pattern_registry.py に移植されている
- [ ] CompiledPatternCache クラスが実装されている
- [ ] 元の spice_guard.py から UNIVERSAL_PATTERNS と GENRE_PATTERNS の定義が削除されている
- [ ] 元の spice_guard.py から pattern_registry.py へのインポートが追加されている
- [ ] 元の spice_guard.py が pattern_registry.py から UNIVERSAL_PATTERNS と GENRE_PATTERNS を参照している
- [ ] pattern_registry.py の構文チェックがエラーなく通る
- [ ] spice_guard.py の構文チェックがエラーなく通る
- [ ] pattern_registry.py の基本的な単体テストが PASS する