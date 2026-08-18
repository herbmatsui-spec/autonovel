# 48ステップ実装計画のステップ8をさらに小さなステップに分解

## ステップ8: 修正 - テスト環境エラー修正（`prometheus_client` 未インストール）
### 元の目的: 即時対応可能なテストエラーを解消する

### さらに細分化されたサブステップ（各ステップ3-5分で完了）

#### ステップ8-1: requirements.txt ファイルを開く
- **アクション**: `/home/herbmatsui/autonovel/requirements.txt` を開く
- **確認**: ファイルが正常に開けること
- **出力**: ファイル内容が表示される

#### ステップ8-2: prometheus-client が含まれているか確認する
- **アクション**: ファイル内容を読んで `prometheus-client` または `prometheus_client` を検索する
- **確認**: 文字列が見つかるか確認する
- **ツール**: `grep -i "prometheus" /home/herbmatsui/autonovel/requirements.txt`
- **判定**: 含まれている場合は「あり」、含まれていない場合は「なし」を記録する

#### ステップ8-3: prometheus-client が含まれていない場合は追加する準備をする
- **アクション**: 含まれていない場合、適切なバージョンを指定して追加する準備をする
- **確認**: 追加する文字列を準備する（例: `prometheus-client>=0.19.0`）
- **判定**: 追加する内容を決定する

#### ステップ8-4: requirements.txt に prometheus-client を追加する
- **アクション**: ファイルの適切な場所（アルファベット順または既存のパターンに従って）に、ステップ8-3 で準備した文字列を追加する
- **確認**: ファイルに正しく追加されていること
- **ツール**: `edit` ツールを使って追加する

#### ステップ8-5: 追加後の requirements.txt 内容を確認する
- **アクション**: 変更後のファイルを読む
- **確認**: `prometheus-client` が正しく追加されていること
- **判定**: 追加が成功したか確認する

#### ステップ8-6: 依存関係を再インストールする準備をする
- **アクション**: `pip install -r requirements.txt` コマンドを実行する準備をする
- **確認**: コマンドが実行可能であることを確認する
- **判定**: pip が利用可能であることを確認する

#### ステップ8-7: 依存関係を再インストールする
- **アクション**: 準備したコマンドを実行する
- **確認**: コマンドが正常に完了すること
- **判定**: インストールが成功したことを確認する（タイムアウトに注意し、必要なら長めに設定）

#### ステップ8-8: テスト環境で prometheus-client が利用可能か確認する
- **アクション**: Python インタプリタで `import prometheus_client` を試す
- **確認**: エラーなくインポートできること
- **ツール**: `python -c "import prometheus_client; print('Import successful')"`

#### ステップ8-9: 問題のテストファイルを特定する
- **アクション**: ステップ1で確認したように、`tests/test_api_integration.py` の collection エラーが原因か確認する
- **確認**: ファイルが存在し、問題のテストがあるか確認する
- **ツール**: `ls /home/herbmatsui/autonovel/tests/test_api_integration.py`

#### ステップ8-10: テストの collection を試してみる
- **アクション**: `pytest /home/herbmatsui/autonovel/tests/test_api_integration.py --collect-only` を実行する
- **確認**: エラーが出ないこと（以前は collection エラーがあったはず）
- **判定**: collection が正常に動作するか確認する

#### ステップ8-11: もしまだエラーが出る場合は詳細を確認する
- **アクション**: エラーが出る場合は、エラー内容を確認してさらに対応が必要か判断する
- **確認**: エラーが prometheus-client 関連かどうかを確認する
- **対応**: 必要ならさらに調査するが、基本的な対応はこれで完了とする

#### ステップ8-12: 作業の完了を宣言する
- **アクション**: ステップ8のすべてのマイクロステップが完了したことを記録する
- **確認**: 次のステップに進む準備ができていること

## 完了基準
- [ ] `requirements.txt` に `prometheus-client` が追加されている
- [ ] バージョン指定が適切であること（例: `prometheus-client>=0.19.0`）
- [ ] `pip install -r requirements.txt` が正常に完了している
- [ ] Python インタプリタで `import prometheus_client` がエラーなく行える
- [ ] `pytest tests/test_api_integration.py --collect-only` がエラーなしで完走する
- [ ] 以前は collection エラーがあったテストが、今では正常に collection できること