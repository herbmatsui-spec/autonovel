# 48ステップ実装計画のステップ10をさらに小さなステップに分解

## ステップ10: 修正 - かんたんモードマジック値外部化
### 元の目的: `src/easy_mode/pipeline.py` のハードコード値をプリセット YAML へ移動する

### さらに細分化されたサブステップ（各ステップ3-5分で完了）

#### ステップ10-1: 対象ファイルを開く
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/pipeline.py` を開く
- **確認**: ファイルが正常に開けること
- **出力**: ファイル内容が表示される

#### ステップ10-2: ハードコードされたマジック値を探す
- **アクション**: ファイル内で数値リテラル（特にepisode構造に関連しそうな数字）を検索する
- **確認**: エピソード構造に関連しそうなハードコードされた値を見つける
- **ツール**: `grep -n "[0-9]\+" /home/herbmatsui/autonovel/src/easy_mode/pipeline.py | head -20`
- **判定**: エピソード構造に関連しそうな値（例: humiliation_ep, trigger_ep など）を特定する

#### ステップ10-3: 検索結果からエピソード構造に関連する値を特定する
- **アクション**: ステップ10-2 の結果を見て、エピソード構造に関連しそうなコメントや変数名の近くにある数値を特定する
- **確認**: humiliation_ep, trigger_ep, musou_start_ep, final_ep, tension_threshold などのパラメータに関連する値を見つける
- **出力**: 各パラメータの現在のハードコードされた値をメモする

#### ステップ10-4: プリセットディレクトリの構造を確認する
- **アクション**: `/home/herbmatsui/autonovel/src/presets/` ディレクトリの内容を確認する
- **確認**: ディレクトリが存在し、ジャンルごとの YAML ファイルがあること
- **ツール**: `ls /home/herbmatsui/autonovel/src/presets/`

#### ステップ10-5: 既存のプリセット YAML ファイルの構造を確認する
- **アクション**: 1つのプリセットファイル（例: zarma.yaml）を開いて内容を確認する
- **確認**: YAML ファイルの構造と既に含まれているキーを把握する
- **ツール**: `cat /home/herbmatsui/autonovel/src/presets/zarma.yaml`
- **判定**: episode_structure セクションを追加できる場所を確認する

#### ステップ10-6: episode_structure セクションのフォーマットを決める
- **アクション**: YAML に追加する episode_structure セクションの構造を決定する
- **確認**: 必要なフィールド（humiliation_ep, trigger_ep, musou_start_ep, final_ep, tension_threshold など）をリストアップする
- **作業内容**の例:
  ```yaml
  episode_structure:
    humiliation_ep: 2
    trigger_ep: 3
    musou_start_ep: 4
    final_ep: 8
    tension_threshold: 75
  ```

#### ステップ10-7: 全ジャンル分のプリセット YAML ファイルに episode_structure セクションを追加する準備をする
- **アクション**: 各ジャンルの YAML ファイルに、ステップ10-6 で決めた構造を追加する準備をする
- **確認**: 追加する内容をジャンルごとに適切な値で準備する
- **判定**: デフォルト値を決めるか、ジャンルごとに異なる値を設定するかを決める

#### ステップ10-8: デフォルトプリセットを作成する準備をする
- **アクション**: エピソード構造のデフォルト値を定義する default_preset.yaml を作成する準備をする
- **確認**: デフォルト値を決定する
- **作業内容**の例:
  ```yaml
  episode_structure:
    humiliation_ep: 2
    trigger_ep: 3
    musou_start_ep: 4
    final_ep: 8
    tension_threshold: 75
  ```

#### ステップ10-9: 各ジャンルのプリセットファイルに episode_structure セクションを追加する（ループの準備）
- **アクション**: すべてのジャンルファイルに対して同じ処理を行う準備をする
- **確認**: 処理対象のファイルリストを作成する
- **ツール**: `ls /home/herbmatsui/autonovel/src/presets/*.yaml`

#### ステップ10-10: 最初のプリセットファイルを開く
- **アクション**: 最初のプリセットファイル（例: zarma.yaml）を開く
- **確認**: ファイルが正常に開けること

#### ステップ10-11: ファイルの末尾に episode_structure セクションを追加する準備をする
- **アクション**: ファイルの末尾に、ステップ10-6 で決めた構造を追加する準備をする
- **確認**: 追加する文字列を準備する（改行を考慮する）
- **作業内容**の例:
  ```
  
  episode_structure:
    humiliation_ep: 2
    trigger_ep: 3
    musou_start_ep: 4
    final_ep: 8
    tension_threshold: 75
  ```

#### ステップ10-12: プリセットファイルに episode_structure セクションを追加する
- **アクション**: ステップ10-11 で準備した文字列をファイルの末尾に追加する
- **確認**: 追加が正しく行われていること
- **ツール**: `edit` ツールを使って追加する（またはファイルを読んで末尾に追加して書き戻す）

#### ステップ10-13: 追加後のファイルを確認する
- **アクション**: 変更後のファイルを読む
- **確認**: episode_structure セクションが正しく追加されていること
- **判定**: YAML として正しく解析できるか確認する

#### ステップ10-14: 残りのプリセットファイルにも同様に追加する
- **アクション**: ステップ10-10 から ステップ10-13 を繰り返して、すべてのプリセットファイルに episode_structure セクションを追加する
- **確認**: すべてのファイルに追加が完了していること
- **判定**: ジャンルごとに適切な値（必要なら異なる値）を設定しているか確認する

#### ステップ10-15: デフォルトプリセットファイルを作成する
- **アクション**: `/home/herbmatsui/autonovel/src/presets/default_preset.yaml` を作成する
- **確認**: ファイルが正常に作成されること
- **ツール**: `write` ツールを使ってファイルを作成する

#### ステップ10-16: デフォルトプリセットファイルに内容を書き込む
- **アクション**: ステップ10-8 で決めたデフォルト値をファイルに書き込る
- **確認**: ファイルに正しく内容が書き込まれていること
- **ツール**: `write` ツールを使って内容を書き込む

#### ステップ10-17: pipeline.py でプリセットローダーを確認する
- **アクション**: pipeline.py でプリセットを読み込んでいる部分を確認する
- **確認**: プリセットローダーがどのように機能しているか把握する
- **参考**: `presets.loader` や同様のモジュールを参照しているか確認する

#### ステップ10-18: pipeline.py の _generate_bike 関数を確認する
- **アクション**: pipeline.py の `_generate_bible` 関数（または類似の名前）を確認する
- **確認**: 現在プリセットからどのように値を取得しているか確認する
- **判定**: エピソード構造関連の値をどこで取得しているか特定する

#### ステップ10-19: pipeline.py でエピソード構造値を取得する部分を特定する
- **アクション**: humiliation_ep, trigger_ep などの変数が設定されている場所を特定する
- **確認**: 現在ハードコードされた値が設定されている場所を見つける
- **ツール**: `grep -n "humiliation_ep\|trigger_ep\|musou_start_ep\|final_ep\|tension_threshold" /home/herbmatsui/autonovel/src/easy_mode/pipeline.py`

#### ステップ10-20: ハードコードされた値をプリセットから取得するように変更する準備をする
- **アクション**: 各変数について、プリセットから `episode_structure` セクションを取得して値を得るように変更する準備をする
- **確認**: 変更後のコード構造を考える
- **作業内容**の例:
  ```python
  # 変更前
  humiliation_ep = 2
  
  # 変更後
  humiliation_ep = preset.get("episode_structure", {}).get("humiliation_ep", 2)
  ```

#### ステップ10-21: 変更するコードを最終決定する
- **アクション**: ステップ10-20 のパターンを基に、すべてのエピソード構造関連の変数について変更方法を決める
- **確認**: デフォルト値を保持しつつ、プリセットから値を取得する方法を決定する
- **判定**: `preset.get("episode_structure", {}).get("key", default_value)` のパターンを使用する

#### ステップ10-22: 最初の変数の変更コードを準備する
- **アクション**: humiliation_ep 変数について、変更前後のコードを準備する
- **確認**: 変更前後のコードが明確であること

#### ステップ10-23: 最初の変数を変更する
- **アクション**: 特定した humiliation_ep 変数の行を、ステップ10-22 で準備した新しいコードに置換する
- **確認**: 置換が正しく行われたこと
- **ツール`: `edit` ツールを使って正確に置換する

#### ステップ10-24: 残りの変数も同様に変更する
- **アクション**: ステップ10-23 を trigger_ep, musou_start_ep, final_ep, tension_threshold について繰り返す
- **確認**: すべての変数が変更されていること
- **判定**: 置換が正しく行われたか確認する

#### ステップ10-25: 変更後のファイルを読んで確認する
- **アクション**: 変更後の `/home/herbmatsui/autonovel/src/easy_mode/pipeline.py` を読む
- **確認**: ハードコードされた値がプリセットから取得するコードに置換されていること
- **判定**: 置換が意図通りに行われたか確認する

#### ステップ10-26: 変更後のファイル全体の構文を確認する準備をする
- **アクション**: Python の構文チェックコマンドを準備する
- **確認**: コマンドが実行可能であることを確認する
- **ツール**: `python -m py_compile /home/herbmatsui/autonovel/src/easy_mode/pipeline.py`

#### ステップ10-27: 構文チェックを実行する
- **アクション**: 準備した構文チェックコマンドを実行する
- **確認**: エラーが出ないこと（何も表示されないのが正常）
- **判定**: 構文エラーがないか確認する

#### ステップ10-28: プリセットから値を取得するロジックをテストする準備をする
- **アクション**: 新しいロジックが正しく動作するかテストする準備をする
- **確認**: テスト用スクリプトを作成できること

#### ステップ10-29: プリセットロジックテストスクリプトを作成する
- **アクション**: プリセット YAML を読んで、episode_structure から値を取得するロジックをテストするスクリプトを作成する
- **確認**: ファイルが正常に作成できること
- **作業内容**の例:
  ```python
  import yaml
  import os
  
  # デフォルトプリセットを読む
  default_preset_path = "/home/herbmatsui/autonovel/src/presets/default_preset.yaml"
  with open(default_preset_path, 'r') as f:
      default_preset = yaml.safe_load(f)
  
  # episode_structure から値を取得するロジックをテスト
  humiliation_ep = default_preset.get("episode_structure", {}).get("humiliation_ep", 2)
  trigger_ep = default_preset.get("episode_structure", {}).get("trigger_ep", 3)
  
  # 期待する値と比較
  assert humiliation_ep == 2, f"Expected humiliation_ep=2, got {humiliation_ep}"
  assert trigger_ep == 3, f"Expected trigger_ep=3, got {trigger_ep}"
  
  print("Preset value extraction test passed")
  ```

#### ステップ10-30: プリセットロジックテストを実行する
- **アクション**: ステップ10-29 で作成したテストスクリプトを実行する
- **確認**: エラーなく実行でき、「Preset value extraction test passed」と出力されること
- **判定**: プリセットから値を取得するロジックが正しく動作することを確認する

#### ステップ10-31: カスタムプリセットでオーバーライドできるかテストする準備をする
- **アクション**: カスタム値を指定したプリセットで、正しくオーバーライドされるかテストする準備をする
- **確認**: テスト用のカスタムプリセットファイルを作成できること

#### ステップ10-32: カスタムプリセットテストスクリプトを作成する
- **アクション**: カスタム値を含むプリセットを作成して、オーバーライドが機能するかテストするスクリプトを作成する
- **確認**: ファイルが正常に作成できること
- **作業内容**の例:
  ```python
  import yaml
  import os
  import tempfile
  
  # 一時ディレクトリにカスタムプリセットを作成
  with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
      custom_preset = {
          "episode_structure": {
              "humiliation_ep": 5,  # カスタム値
              "trigger_ep": 10      # カスタム値
          }
      }
      yaml.dump(custom_preset, f)
      custom_preset_path = f.name
  
  try:
      # カスタムプリセットを読む
      with open(custom_preset_path, 'r') as f:
          preset = yaml.safe_load(f)
      
      # episode_structure から値を取得するロジックをテスト
      humiliation_ep = preset.get("episode_structure", {}).get("humiliation_ep", 2)
      trigger_ep = preset.get("episode_structure", {}).get("trigger_ep", 3)
      
      # カスタム値が反映されているか確認
      assert humiliation_ep == 5, f"Expected humiliation_ep=5, got {humiliation_ep}"
      assert trigger_ep == 10, f"Expected trigger_ep=10, got {trigger_ep}"
      
      print("Custom preset override test passed")
  finally:
      # 一時ファイルを削除
      os.unlink(custom_preset_path)
  ```

#### ステップ10-33: カスタムプリセットテストを実行する
- **アクション**: ステップ10-32 で作成したテストスクリプトを実行する
- **確認**: エラーなく実行でき、「Custom preset override test passed」と出力されること
- **判定**: カスタムプリセットでオーバーライドが正しく機能することを確認する

#### ステップ10-34: 作業の完了を宣言する
- **アクション**: ステップ10のすべてのマイクロステップが完了したことを記録する
- **確認**: 次のステップに進む準備ができていること

## 完了基準
- [ ] src/presets/ ディレクトリのすべての YAML ファイルに episode_structure セクションが追加されている
- [ ] 各ファイルに適切な値（ humiliation_ep, trigger_ep, musou_start_ep, final_ep, tension_threshold ）が設定されている
- [ ] src/presets/default_preset.yaml が作成され、デフォルト値が設定されている
- [ ] src/easy_mode/pipeline.py のハードコードされた値が、プリセットから取得するロジックに置換されている
- [ ] 置換後のコードが `preset.get("episode_structure", {}).get("key", default_value)` という形式になっている
- [ ] Python 構文チェックでエラーが出ない
- [ ] プリセットから値を取得するロジックが正しく動作すること
- [ ] カスタムプリセットでオーバーライドが正しく機能すること
- [ ] ハードコードされたマジック値がコード上から消えていること