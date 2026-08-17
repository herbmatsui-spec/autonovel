# 48ステップ実装計画のステップ4をさらに小さなステップに分解

## ステップ4: 実装 - `UltimateHegemonyEngine` 新コンストラクタの実装
### 元の目的: 12 個の依存を明示的に受け取る新コンストラクタを実装する

### さらに細分化されたサブステップ（各ステップ3-5分で完了）

#### ステップ4-1: 変更対象のファイルを開く
- **アクション**: `/home/herbmatsui/autonovel/src/backend/engine.py` を開く
- **確認**: ファイルが正常に開けること
- **出力**: エディタでファイル内容が表示される

#### ステップ4-2: `__init__` メソッドの場所を特定する
- **アクション**: ファイル内で `def __init__` を検索する
- **確認**: メソッド定義の場所を見つける（行番号をメモ）
- **ツール**: `grep -n "def __init__" /home/herbmatsui/autonovel/src/backend/engine.py`

#### ステップ4-3: 現在の `__init__` シグネチャを確認する
- **アクション**: 特定した行周辺のコードを読む（5行程度前後）
- **確認**: 現在の引数リストを確認する
- **出力**: 現在のコンストラクタの引数を把握する

#### ステップ4-4: ステップ3の設計書を参照する
- **アクション**: `/home/herbmatsui/autonovel/proposals/engine_refactor_spec.md` を開く
- **確認**: ファイルが開け、設計された新しいシグネチャを確認できること
- **出力**: 目標とする新しいコンストラクタシグネチャを把握する

#### ステップ4-5: 新コンストラクタシグネチャの草稿を作成する
- **アクション**: ステップ3の設計結果に基づいて、新しい `__init__` シグネチャを文字列で準備する
- **確認**: すべての依存を含むシグネチャ草稿が作成できること
- **作業内容**: 
  ```
  def __init__(
      self,
      planner: Optional["PlanningAgent"] = None,
      writer: Optional["WritingAgent"] = None,
      pm: Optional["ProjectManager"] = None,
      ctx_mgr: Optional["ContextManager"] = None,
      formatter: Optional["Formatter"] = None,
      validator: Optional["Validator"] = None,
      auditor: Optional["Auditor"] = None,
      narrative: Optional["NarrativeAgent"] = None,
      critique: Optional["CritiqueAgent"] = None,
      marketing: Optional["MarketingAgent"] = None,
      bible_agent: Optional["BibleAgent"] = None,
      plot_agent: Optional["PlotAgent"] = None,
      style_rag: Optional["StyleRag"] = None,
      api_key: Optional[str] = None,
      repo: Optional["Repository"] = None,
      db: Optional["DatabaseManager"] = None,
      llm: Optional["LLMService"] = None,
      cooldown: Optional[float] = None,
      plot_service: Optional["PlotService"] = None,
      **legacy
  ) -> None:
  ```

#### ステップ4-6: DeprecationWarning を発火するコードの準備をする
- **アクション**: `**legacy` が使われている場合に警告を発火するコードを準備する
- **確認**: `warnings.warn` を使った `DeprecationWarning` の発火方法を確認する
- **作業内容**: 
  ```python
  import warnings
  if legacy:
      warnings.warn(
          "The 'legacy' parameter is deprecated and will be removed in a future version.",
          DeprecationWarning,
          stacklevel=2
      )
  ```

#### ステップ4-7: 各依存をインスタンス変数に設定するコードの準備をする（前半分）
- **アクション**: planner から formatter までの依存を `self.XXX = XXX or self._legacy_dep('XXX')` という形式で設定するコードを準備する
- **確認**: 各依存の設定コードが作成できること
- **作業内容**の例:
  ```python
  self.planner = planner or self._legacy_dep('planner')
  self.writer = writer or self._legacy_dep('writer')
  self.pm = pm or self._legacy_dep('pm')
  self.ctx_mgr = ctx_mgr or self._legacy_dep('ctx_mgr')
  self.formatter = formatter or self._legacy_dep('formatter')
  ```

#### ステップ4-8: 各依存をインスタンス変数に設定するコードの準備をする（後半分）
- **アクション**: validator から style_rag までの依存を同様に設定するコードを準備する
- **確認**: 各依存の設定コードが作成できること
- **作業内容**の例:
  ```python
  self.validator = validator or self._legacy_dep('validator')
  self.auditor = auditor or self._legacy_dep('auditor')
  self.narrative = narrative or self._legacy_dep('narrative')
  self.critique = critique or self._legacy_dep('critique')
  self.marketing = marketing or self._legacy_dep('marketing')
  self.bible_agent = bible_agent or self._legacy_dep('bible_agent')
  self.plot_agent = plot_agent or self._legacy_dep('plot_agent')
  self.style_rag = style_rag or self._legacy_dep('style_rag')
  ```

#### ステップ4-9: api_key から plot_service までの依存を設定するコードの準備をする
- **アクション**: 残りの依存（api_key, repo, db, llm, cooldown, plot_service）を設定するコードを準備する
- **確認**: 各依存の設定コードが作成できること
- **作業内容**の例:
  ```python
  self.api_key = api_key
  self.repo = repo
  self.db = db
  self.llm = llm
  self.cooldown = cooldown
  self.plot_service = plot_service
  ```

#### ステップ4-10: 変更する範囲を特定する（開始位置）
- **アクション**: `__init__` メソッドの本体（インデントが始まる場所）を見つける
- **確認**: 変更を開始する行番号を特定する
- **ツール**: 行番号を基に、現在の `__init__` 本体の開始位置を確認する

#### ステップ4-11: 変更する範囲を特定する（終了位置）
- **アクション**: `__init__` メソッドの終了位置を見つける
- **確認**: 次のメソッドまたはクラス定義の開始位置を確認し、その直前が `__init__` の終了位置であることを確認する
- **ツール**: 次の `def ` または `class ` の行番号を確認する

#### ステップ4-12: 変更する文字列全体を準備する（準備段階）
- **アクション**: ステップ4-5 から ステップ4-9 までのコードを組み合わせて、完全な新しい `__init__` メソッド本体を準備する
- **確認**: 変更すべき文字列と置き換える新しい文字列が準備できること
- **注意**: インデント（4スペースまたは1タブ）を正確に保つこと

#### ステップ4-13: バックアップを取るために元のファイルを読む
- **アクション**: 変更前に元のファイル内容を読んでバックアップとして保存する
- **確認**: ファイル内容が正しく読み取れること
- **目的**: 変更後に元に戻す必要が生じた場合のため

#### ステップ4-14: `__init__` メソッドを置換する
- **アクション**: ステップ4-10 と ステップ4-11 で特定した範囲を、ステップ4-13 で準備した新しい文字列に置換する
- **ツール**: `edit` ツールを使って正確に置換する
- **確認**: 置換が正しく行われたこと

#### ステップ4-15: 置換後のファイルを読んで確認する
- **アクション**: 変更後の `/home/herbmatsui/autonovel/src/backend/engine.py` を読む
- **確認**: 新しい `__init__` メソッドが正しく配置されていること
- **判定**: 置換が意図通りに行われたか確認する

#### ステップ4-16: `import warnings` 文の追加が必要か確認する
- **アクション**: ファイルの上部に `import warnings` が既にあるか確認する
- **確認**: ない場合は追加する必要があることを確認する
- **ツール**: `head -20 /home/herbmatsui/autonovel/src/backend/engine.py | grep -n "import warnings"`

#### ステップ4-17: `import warnings` 文を追加する（必要な場合）
- **アクション**: `import warnings` がない場合、ファイルの適切な場所（他の import 文の近く）に追加する
- **確認**: 文が正しく追加されていること
- **ツール**: ファイルの先頭付近を読んで、import ブロックを見つける

#### ステップ4-18: 警告発火コードを配置する場所を決める
- **アクション**: `__init__` メソッド本体の最初に警告発火コードを配置する場所を決める
- **確認**: 依存設定より前に配置すべきか、または特定の場所に配置すべきかを決定する
- **判定**: 依存チェックより前に配置する（legacy が空かどうかを早期にチェックするため）

#### ステップ4-19: 警告発火コードを配置する準備をする
- **アクション**: ステップ4-6 のコードを、`__init__` メソッドの先頭に配置するために準備する
- **確認**: インデントを考慮した形でコードが準備できること

#### ステップ4-20: 警告発火コードを追加する
- **アクション**: `__init__` メソッドの最初の行に、ステップ4-19 の警告発火コードを追加する
- **ツール**: `edit` ツールを使って特定の場所に挿入する
- **確認**: コードが正しく追加されていること

#### ステップ4-21: 変更後のファイル全体の構文を確認する準備をする
- **アクション: Python の構文チェックコマンドを準備する
- **確認**: コマンドが実行可能であることを確認する
- **ツール**: `python -m py_compile /home/herbmatsui/autonovel/src/backend/engine.py`

#### ステップ4-22: 構文チェックを実行する
- **アクション**: 準備した構文チェックコマンドを実行する
- **確認**: エラーが出ないこと（何も表示されないのが正常）
- **判定**: 構文エラーがないか確認する

#### ステップ4-23: mypy 型チェックを実行する準備をする
- **アクション**: mypy 型チェックコマンドを準備する
- **確認**: 設定ファイルを指定して実行できることを確認する
- **ツール**: `mypy --config-file /home/herbmatsui/autonovel/pyproject.toml /home/herbmatsui/autonovel/src/backend/engine.py`

#### ステップ4-24: mypy 型チェックを実行する
- **アクション**: 準備した mypy チェックコマンドを実行する
- **確認**: エラーが出ないこと
- **判定**: 型エラーがないか確認する（目標: エラー 0 件）

#### ステップ4-25: インスタンス化テストを行う準備をする
- **アクション**: 新しいコンストラクタでインスタンス化できるかテストする準備をする
- **確認**: テスト用の小さな Python スクリプトを作成できること
- **作業内容**: 
  ```python
  from src.backend.engine import UltimateHegemonyEngine
  # 基本的なインスタンス化テスト
  engine = UltimateHegemonyEngine()
  print("Basic instantiation successful")
  ```

#### ステップ4-26: インスタンス化テストスクリプトを作成する
- **アクション**: 一時ファイルにテストスクリプトを作成する
- **確認**: ファイルが正常に作成できること
- **ファイル名**: `/tmp/test_engine_instantiation.py` または同様の一時場所

#### ステップ4-27: インスタンス化テストを実行する
- **アクション**: ステップ4-26 で作成したテストスクリプトを実行する
- **確認**: エラーなく実行でき、「Basic instantiation successful」と出力されること
- **判定**: 基本的なインスタンス化が成功することを確認する

#### ステップ4-28: DeprecationWarning が発火するかテストする準備をする
- **アクション**: `**legacy` に何かを渡すと警告が発火するかテストする準備をする
- **確認**: 警告をキャプチャして確認できるテストスクリプトを作成できること

#### ステップ4-29: 警告発火テストスクリプトを作成する
- **アクション**: 警告をキャプチャするテストスクリプトを作成する
- **確認**: ファイルが正常に作成できること
- **作業内容**の例:
  ```python
  import warnings
  from src.backend.engine import UltimateHegemonyEngine
  
  with warnings.catch_warnings(record=True) as w:
      warnings.simplefilter("always")
      engine = UltimateHegemonyEngine(legacy={"dummy": "value"})
      if w:
          for warning in w:
              if issubclass(warning.category, DeprecationWarning):
                  print("DeprecationWarning successfully fired:")
                  print(warning.message)
                  break
          else:
              print("No DeprecationWarning found")
      else:
          print("No warnings captured")
  ```

#### ステップ4-30: 警告発火テストを実行する
- **アクション**: ステップ4-29 で作成したテストスクリプトを実行する
- **確認**: DeprecationWarning が正しく発火すること
- **判定**: 後方互換性のための警告機能が正しく動作することを確認する

#### ステップ4-31: 変更を元に戻す準備（万が一のため）
- **アクション**: 変更後に問題が生じた場合のために、元の状態に戻す方法を確認しておく
- **確認**: git やバックアップファイルを使って復元できる方法を知っていること

#### ステップ4-32: 作業の完了を宣言する
- **アクション**: ステップ4のすべてのマイクロステップが完了したことを記録する
- **確認**: 次のステップに進む準備ができていること

## 完了基準
- [ ] `src/backend/engine.py` の `__init__` が新しいシグネチャに置換されている
- [ ] 全 19 個の依存が明示的コンストラクタ引数として定義されている
- [ ] `_legacy` 辞書は残っているが、使用時に `DeprecationWarning` を発火する
- [ ] すべての型ヒントが `Optional[T] = None` の形式で明示されている
- [ ] `mypy --strict src/backend/engine.py` でエラーが 0 件
- [ ] Python 構文チェックでエラーが出ない
- [ ] 基本的なインスタンス化が成功する
- [ ] `legacy` パラメータを渡すと `DeprecationWarning` が発火する