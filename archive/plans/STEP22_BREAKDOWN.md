# 48ステップ実装計画のステップ22をさらに小さなステップに分解

## ステップ22: 実装 - `spice_guard/extractor.py` と `marker.py` の抽出
### 元の目的: 抽出・マーカー操作を独立モジュール化する

### さらに細分化されたサブステップ（各ステップ3-5分で完了）

#### ステップ22-1: 対象ディレクトリを確認する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/` ディレクトリの内容を確認する
- **確認**: ディレクトリが存在し、pattern_registry.py が作成されていること
- **ツール**: `ls -la /home/herbmatsui/autonovel/src/easy_mode/spice_guard/`

#### ステップ22-2: 既存の extractor.py と marker.py を確認する（ある場合）
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/extractor.py` と `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/marker.py` が存在するか確認する
- **確認**: 存在する場合は内容を確認し、どこまで実装されているか判断する
- **ツール**: `ls /home/herbmatsui/autonovel/src/easy_mode/spice_guard/extractor.py`、`ls /home/herbmatsui/autonovel/src/easy_mode/spice_guard/marker.py`

#### ステップ22-3: SpiceGuard.py から抽出ロジックを特定する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` から抽出に関連するメソッドを特定する
- **確認**: 抽出ロジック（SpiceElement の抽出）を担当するメソッドを見つける
- **ツール**: `grep -n "def " /home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` と組み合わせて抽出関連のメソッドを探す

#### ステップ22-4: 抽出ロジックの詳細を確認する
- **アクション**: 抽出に関連するメソッドの内容を読む
- **確認**: 抽出ロジックの実装詳細を把握する
- **出力**: 抽出ロジックの構造と処理フローをメモする

#### ステップ22-5: SpiceGuard.py から マーカー操作ロジックを特定する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` からマーカー操作に関連するメソッドを特定する
- **確認**: マーカー注入・除去を担当するメソッドを見つける
- **ツール**: `grep -n "def " /home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` と組み合わせてマーカー関連のメソッドを探す

#### ステップ22-6: マーカー操作ロジックの詳細を確定する
- **アクション**: マーカー操作に関連するメソッドの内容を読む
- **確認**: マーカー操作ロジックの実装詳細を把握する
- **出力**: マーカー操作ロジックの構造と処理フローをメモする

#### ステップ22-7: extractor.py のファイル構造を作成する
- **アクション**: 新しい extractor.py ファイルの基本構造を作成する
- **確認**: ファイルが正常に作成できること
- **作業内容**の例:
  ```python
  """
  SpiceGuard 抽出モジュール
  """
  from __future__ import annotations
  
  from typing import List
  from .pattern_registry import CompiledPatternCache
  
  
  class SpiceExtractor:
      """スパイス要素の抽出を担当するクラス"""
      pass
  ```

#### スteps22-8: marker.py のファイル構造を作成する
- **アクション**: 新しい marker.py ファイルの基本構造を作成する
- **確認**: ファイルが正常に作成できること
- **作業内容**の例:
  ```python
  """
  SpiceGuard マーカー操作モジュール
  """
  from __future__ import annotations
  
  from typing import List
  
  
  class SpiceMarkerInjector:
      """スパイスマーカーの注入を担当するクラス"""
      pass
  
  
  class SpiceMarkerCleaner:
      """スパイスマーカーの除去を担当するクラス"""
      pass
  ```

#### ステップ22-9: extractor.py を作成する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/extractor.py` を作成する
- **確認**: ファイルが正常に作成されること
- **ツール**: `write` ツールを使ってファイルを作成する

#### ステップ22-10: marker.py を作成する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/marker.py` を作成する
- **確認**: ファイルが正常に作成されること
- **ツール**: `write` ツールを使ってファイルを作成する

#### ステップ22-11: 抽出ロジックを extractor.py に移植する準備をする
- **アクション**: ステップ22-4 で特定した抽出ロジックを extractor.py に移植する準備をする
- **確認**: 移植するコードを特定する
- **作業内容**: 抽出に関連するメソッドのコードを特定する

#### ステップ22-12: 抽出ロジックを extractor.py に移植する
- **アクション**: ステップ22-11 で特定したコードを extractor.py に書き込む
- **確認**: コードが正しく移植されていること
- **ツール**: `edit` ツールを使ってファイルに書き込む

#### ステップ22-13: マーカー操作ロジックを marker.py に移植する準備をする
- **アクション**: ステップ22-6 で特定したマーカー操作ロジックを marker.py に移�する準備をする
- **確認**: 移植するコードを特定する
- **作業内容**: マーカー操作に関連するメソッドのコードを特定する

#### ステップ22-14: マーカー操作ロジックを marker.py に移�する
- **アクション**: ステップ22-13 で特定したコードを marker.py に書き込む
- **確認**: コードが正しく移植されていること
- **ツール**: `edit` ツールを使ってファイルに書き込む

#### ステップ22-15: extractor.py に必要なインポートを追加する
- **アクション**: extractor.py が必要とするインポートを追加する準備をする
- **確認**: 必要なインポート（pattern_registry からの CompiledPatternCache など）を特定する
- **作業内容**の例:
  ```python
  from .pattern_registry import CompiledPatternCache
  ```

#### ステップ22-16: extractor.py のインポートを追加する
- **アクション**: extractor.py の上部に必要なインポートを追加する
- **確認**: インポートが正しく追加されていること
- **ツール**: `edit` ツールを使ってインポートブロックに追加する

#### ステップ22-17: marker.py に必要なインポートを追加する
- **アクション**: marker.py が必要とするインポートを追加する準備をする
- **確認**: 必要なインポートを特定する
- **作業内容**の例: マーカー操作には特別なインポートが不要な場合もある

#### ステップ22-18: marker.py のインポートを追加する
- **アクション**: marker.py の上部に必要なインポートを追加する
- **確認**: インポートが正しく追加されていること
- **ツール**: `edit` ツールを使ってインポートブロックに追加する

#### ステップ22-19: 元の spice_guard.py から 抽出ロジックを削除する準備をする
- **アクション**: 元のファイルからコピーした抽出ロジックを削除する準備をする
- **確認**: 削除する範囲を特定する
- **作業内容**: 抽出に関連するメソッドの定義範囲を特定する

#### ステップ22-20: 元の spice_guard.py から 抽出ロジックを削除する
- **アクション**: 特定した抽出ロジックの定義範囲を、空白またはコメントに置換する
- **確認**: 削除が正しく行われたこと
- **ツール**: `edit` ツールを使って置換する

#### ステップ22-21: 元の spice_guard.py から マーカー操作ロジックを削除する準備をする
- **アクション**: 元のファイルからコピーしたマーカー操作ロジックを削除する準備をする
- **確認**: 削除する範囲を特定する
- **作業内容**: マーカー操作に関連するメソッドの定義範囲を特定する

#### ステップ22-22: 元の spice_guard.py から マーカー操作ロジックを削除する
- **アクション**: 特定したマーカー操作ロジックの定義範囲を、空白またはコメントに置換する
- **確認**: 削除が正しく行われたこと
- **ツール**: `edit` ツールを使って置換する

#### ステップ22-23: 元の spice_guard.py に extractor.py と marker.py からのインポートを追加する準備をする
- **アクション**: 元のファイルの上部に、extractor.py と marker.py から必要なものをインポートするコードを追加する準備をする
- **確認**: インポート文が正しく追加されること
- **作業内容**の例:
  ```python
  from .extractor import SpiceExtractor
  from .marker import SpiceMarkerInjector, SpiceMarkerCleaner
  ```

#### ステップ22-24: 元の spice_guard.py のインポートを追加する
- **アクション**: 元のファイルの上部のインポートブロックに、ステップ22-23 で準備したインポート文を追加する
- **確認**: インポートが正しく追加されていること
- **ツール**: `edit` ツールを使ってインポートブロックに追加する

#### ステップ22-25: 元の spice_guard.py で 抽出ロジックを参照している場所を更新する
- **アクション**: 元のファイル内で 抽出ロジックを参照している場所を、新しいインポート先を参照するように変更する
- **確認**: 参照が正しく更新されていること
- **作業内容**: 抽出ロジックを呼び出していた場所を、SpiceExtractor クラスのメソッド呼び出しに変更する

#### ステップ22-26: 元の spice_guard.py で マーカー操作ロジックを参照している場所を更新する
- **アクション**: 元のファイル内で マーカー操作ロジックを参照している場所を、新しいインポート先を参照するように変更する
- **確認**: 参照が正しく更新されていること
- **作業内容**: マーカー操作ロジックを呼び出していた場所を、SpiceMarkerInjector/SpiceMarkerCleaner クラスのメソッド呼び出しに変更する

#### ステップ22-27: 変更後の spice_guard.py を読んで確信する
- **アクション**: 変更後の `/home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` を読む
- **確認**: 抽出ロジックとマーカー操作ロジックが削除されていること
- **確認**: extractor.py と marker.py からのインポートが追加されていること
- **確認**: 抽出・マーカー操作が新しいクラスを通じて行われていること
- **判定**: 変更が正しく行われているか確認する

#### ステップ22-28: extractor.py の構文を確認する
- **アクション**: `python -m py_compile /home/herbmatsui/autonovel/src/easy_mode/spice_guard/extractor.py` を実行する
- **確認**: エラーが出ないこと
- **判定**: 構文エラーがないか確認する

#### ステップ22-29: marker.py の構文を確認する
- **アクション**: `python -m py_compile /home/herbmatsui/autonovel/src/easy_mode/spice_guard/marker.py` を実行する
- **確認**: エラーが出ないこと
- **判定**: 構文エラーがないか確認する

#### ステップ22-30: spice_guard.py の構文を確認する
- **アクション**: `python -m py_compile /home/herbmatsui/autonovel/src/easy_mode/spice_guard.py` を実行する
- **確認**: エラーが出ないこと
- **判定**: 構文エラーがないか確認する

#### ステップ22-31: 各モジュールの単体テストを作成する準備をする
- **アクション**: extractor.py と marker.py の機能をテストする単体テストを作成する準備をする
- **確認**: テストファイルを作成できること
- **判定**: どのようなテストを行うかを考える

#### ステップ22-32: extractor.py の単体テストファイルを作成する
- **アクション**: `/home/herbmatsui/autonovel/tests/unit/test_spice_guard_extractor.py` を作成する
- **確認**: ファイルが正常に作成されること
- **ツール**: `write` ツールを使ってファイルを作成する

#### ステップ22-33: marker.py の単体テストファイルを作成する
- **アクション**: `/home/herbmatsui/autonovel/tests/unit/test_spice_guard_marker.py` を作成する
- **確認**: ファイルが正常に作成されること
- **ツール**: `write` ツールを使ってファイルを作成する

#### ステップ22-34: 基本的な extractor テストを実装する
- **アクション**: extractor.py が正しくインポートできることと、基本的な機能が動作することをテストする
- **確認**: テストがパスすること
- **作業内容**の例:
  ```python
  from src.easy_mode.spice_guard.extractor import SpiceExtractor
  
  def test_extractor_import():
      """基本的なインポートテスト"""
      assert SpiceExtractor is not None
      extractor = SpiceExtractor()
      assert extractor is not None
  ```

#### ステップ22-35: 基本的な marker テストを実装する
- **アクション**: marker.py が正しくインポートできることと、基本的な機能が動作することをテストする
- **確認**: テストがパスすること
- **作業内容**の例:
  ```python
  from src.easy_mode.spice_guard.marker import SpiceMarkerInjector, SpiceMarkerCleaner
  
  def test_marker_import():
      """基本的なインポートテスト"""
      assert SpiceMarkerInjector is not None
      assert SpiceMarkerCleaner is not None
      injector = SpiceMarkerInjector()
      cleaner = SpiceMarkerCleaner()
      assert injector is not None
      assert cleaner is not None
  ```

#### ステップ22-36: extractor.py と marker.py の単体テストを実行する
- **アクション**: 作成した単体テストを実行する
- **確認**: テストがパスすること
- **判定**: 基本的な機能が正しく動作することを確認する
- **ツール**: `python -m pytest /home/herbmatsui/autonovel/tests/unit/test_spice_guard_extractor.py /home/herbmatsui/autonovel/tests/unit/test_spice_guard_marker.py -v`

#### ステップ22-37: 変更後の spice_guard.py がファサードとして機能するか確認する
- **アクション**: 変更後の spice_guard.py が薄いラッパーとして機能するか確認する
- **確認**: 実際のロジックは extractor.py と marker.py に委譲されていること
- **判定**: ファサードとして適切に機能しているか確認する

#### ステップ22-38: 作業の完了を宣言する
- **アクション**: ステップ22のすべてのマイクロステップが完了したことを記録する
- **確認**: 次のステップに進む準備ができていること

## 完了基準
- [ ] `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/extractor.py` が作成されている
- [ ] `/home/herbmatsui/autonovel/src/easy_mode/spice_guard/marker.py` が作成されている
- [ ] 抽出ロジックが extractor.py に移植されている
- [ ] マーカー操作ロジックが marker.py に移植されている
- [ ] 元の spice_guard.py から 抽出ロジックとマーカー操作ロジックが削除されている
- [ ] 元の spice_guard.py に extractor.py と marker.py からのインポートが追加されている
- [ ] 元の spice_guard.py が extractor.py と marker.py を参照している
- [ ] extractor.py の構文チェックがエラーなく通る
- [ ] marker.py の構文チェックがエラーなく通る
- [ ] spice_guard.py の構文チェックがエラーなく通る
- [ ] extractor.py と marker.py の基本的な単体テストが PASS する
- [ ] spice_guard.py がファサードとして機能している（実際の処理は delegate されている）