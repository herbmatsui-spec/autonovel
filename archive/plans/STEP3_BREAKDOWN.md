# 48ステップ実装計画のステップ3をさらに小さなステップに分解

## ステップ3: 設計 - `UltimateHegemonyEngine` 新コンストラクタ仕様
### 元の目的: リファクタ後のコンストラクタシグネチャを確定する

### さらに細分化されたサブステップ（各ステップ3-5分で完了）

#### ステップ3-1: ステップ1の調査結果を確認する
- **アクション**: `/home/herbmatsui/autonovel/proposals/legacy_deps_inventory.md` を開く
- **確認**: ファイルが存在し、使用中の `_legacy_dep` 依存のリストが確認できること
- **出力**: 使用中の依存名のリストを把握する

#### ステップ3-2: 各依存の型を特定する準備をする
- **アクション**: 各依存がどのクラスまたは型かを調べるための準備
- **確認**: ソースコード内で各依存の定義場所を検索できるようにツールを準備する
- **判定**: `grep` コマンドを使って型情報を調べられることを確認する

#### ステップ3-3: planner 依存の型を特定する
- **アクション**: `planner` 依存の型を調べる
- **確認**: `planner` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Planner" /home/herbmatsui/autonovel/src/` または `grep -r "Planner" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `planner` の型（例: `PlanningAgent` など）を特定する

#### ステップ3-4: writer 依存の型を特定する
- **アクション**: `writer` 依存の型を調べる
- **確認**: `writer` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Writer" /home/herbmatsui/autonovel/src/` または `grep -r "Writer" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `writer` の型を特定する

#### ステップ3-5: pm 依存の型を特定する
- **アクション**: `pm` 依存の型を調べる
- **確認**: `pm` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Pm" /home/herbmatsui/autonovel/src/` または `grep -r "\.pm" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `pm` の型を特定する（ProjectManager の可能性）

#### ステップ3-6: ctx_mgr 依存の型を特定する
- **アクション**: `ctx_mgr` 依存の型を調べる
- **確認**: `ctx_mgr` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*CtxMgr\|class.*ContextMgr" /home/herbmatsui/autonovel/src/` または `grep -r "ctx_mgr" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `ctx_mgr` の型を特定する

#### ステップ3-7: formatter 依存の型を特定する
- **アクション**: `formatter` 依存の型を調べる
- **確認**: `formatter` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Formatter" /home/herbmatsui/autonovel/src/` または `grep -r "formatter" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `formatter` の型を特定する

#### ステップ3-8: validator 依存の型を特定する
- **アクション**: `validator` 依存の型を調べる
- **確認**: `validator` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Validator" /home/herbmatsui/autonovel/src/` または `grep -r "validator" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `validator` の型を特定する

#### ステップ3-9: auditor 依存の型を特定する
- **アクション**: `auditor` 依存の型を調べる
- **確認**: `auditor` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Auditor" /home/herbmatsui/autonovel/src/` または `grep -r "auditor" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `auditor` の型を特定する

#### ステップ3-10: narrative 依存の型を特定する
- **アクション**: `narrative` 依存の型を調べる
- **確認**: `narrative` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Narrative" /home/herbmatsui/autonovel/src/` または `grep -r "narrative" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `narrative` の型を特定する

#### ステップ3-11: critique 依存の型を特定する
- **アクション**: `critique` 依存の型を調べる
- **確認**: `critique` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Critique" /home/herbmatsui/autonovel/src/` または `grep -r "critique" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `critique` の型を特定する

#### ステップ3-12: marketing 依存の型を特定する
- **アクション**: `marketing` 依存の型を調べる
- **確認**: `marketing` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*Marketing" /home/herbmatsui/autonovel/src/` または `grep -r "marketing" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `marketing` の型を特定する

#### ステップ3-13: bible_agent 依存の型を特定する
- **アクション**: `bible_agent` 依存の型を調べる
- **確認**: `bible_agent` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*BibleAgent\|class.*Bible.*Agent" /home/herbmatsui/autonovel/src/` または `grep -r "bible_agent" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `bible_agent` の型を特定する

#### ステップ3-14: plot_agent 依存の型を特定する
- **アクション**: `plot_agent` 依存の型を調べる
- **確認**: `plot_agent` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*PlotAgent\|class.*Plot.*Agent" /home/herbmatsui/autonovel/src/` または `grep -r "plot_agent" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `plot_agent` の型を特定する

#### ステップ3-15: style_rag 依存の型を特定する
- **アクション**: `style_rag` 依存の型を調べる
- **確認**: `style_rag` がどのクラスまたはインターフェースかを特定する
- **ツール**: `grep -r "class.*StyleRag\|class.*Style.*Rag" /home/herbmatsui/autonovel/src/` または `grep -r "style_rag" /home/herbmatsui/autonovel/src/ --include="*.py" | head -5`
- **出力**: `style_rag` の型を特定する

#### ステップ3-16: 依存の型情報をまとめ始める
- **アクション**: これまで特定した型情報を一覧にまとめる
- **確認**: 各依存名と対応する型をリストアップする
- **出力**: 依存名:型 の対応表の草稿を作成する

#### ステップ3-17: コンストラクタ引数の命名規則を確認する
- **アクション**: 既存のコードベースでの命名規則を確認する
- **確認**: スネーク_case か カメルCase か、接頭辞/接尾辞の使用有無などを確認する
- **ツール**: `grep -r "def __init__" /home/herbmatsui/autonovel/src/backend/ --include="*.py" | head -3`
- **出力**: コンストラクタ引数の命名規則を把握する

#### ステップ3-18: デフォルト値と後方互換性の設計を考える
- **アクション**: 各引数のデフォルト値を `None` とするか、`**legacy` を残すかを考える
- **確認**: 後方互換性のために `**legacy` と `DeprecationWarning` をどのように実装するかを設計する
- **出力**: デフォルト値と後方互換性戦略をメモする

#### ステップ3-19: コンストラクタシグネチャの草稿を作成する
- **アクション**: これまでの情報を基に、`__init__` メソッドのシグネチャ草稿を作成する
- **確認**: `def __init__(self, planner: PlannerType = None, writer: WriterType = None, ...) -> None:` という形式の草稿
- **判定**: すべての依存を含んでいるか確認する

#### ステップ3-20: ドキュメント文字列の構想を始める
- **アクション**: コンストラクタの docstring に何を書くかを考える
- **確認**: パラメータの説明、後方互換性に関する注意点などを検討する
- **出力**: docstring の草稿をメモする

#### ステップ3-21: 設計書ファイルの準備をする
- **アクション**: 出力先のファイル `/home/herbmatsui/autonovel/proposals/engine_refactor_spec.md` を確認する
- **確認**: ファイルが存在するか、存在しない場合は新規作成する準備をする
- **判定**: ファイルの状態を確認する

#### ステップ3-22: 設計書にヘッダーを書く
- **アクション**: ファイルにヘッダー情報を書き込む
- **確認**: ファイルが作成/更新されること
- **内容**: 
  ```
  # UltimateHegemonyEngine リファクター仕様書
  作成日: [現在の日付]
  ```

#### ステップ3-23: 設計書にコンストラクタシグネチャを書く
- **アクション**: 草稿で作成したコンストラクタシグネチャをファイルに書き込む
- **確認**: ファイルに正しく記録されること
- **フォーマット**: 
  ```
  ## コンストラクタシグネチャ

  ```python
  def __init__(
      self,
      planner: Optional[PlannerType] = None,
      writer: Optional[WriterType] = None,
      ...  # その他の依存
      **legacy
  ) -> None:
      """UltimateHegemonyEngine のコンストラクタ

      Args:
          planner: プランニングエージェント
          writer: ライティングエージェント
          # ... その他の依存
          **legacy: 後方互換性のためのレガシー依存（非推奨）
      """
  ```
  ```

#### ステップ3-24: 設計書に型ヒントの説明を追加する
- **アクション**: 各型ヒントの具体的な型を書き込む
- **確認**: ファイルに型情報が正しく記録されること
- **出力**: 各引数の具体的型（例: `Optional["PlanningAgent"] = None`）を記述

#### ステップ3-25: 設計書の内容を確認する
- **アクション**: 作成したファイルの内容を読み返す
- **確認**: 必要な情報（シグネチャ、型ヒント、docstring）がすべて含まれていること
- **判定**: 設計目的が達成されているか確認する

#### ステップ3-26: 作業の完了を宣言する
- **アクション**: ステップ3の作業が完了したことを記録する
- **確認**: 次のステップに進む準備ができていること