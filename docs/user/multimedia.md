# Multimedia ユーザーマニュアル

## Asset Pack を生成する

1. スタジオワークスペースを開く
2. 画面左のサイドバー下部の **🎬 Multimedia** タブをクリック
3. 含めたい成果物 (IF Routes / Media Mix / eBook) にチェック
4. eBook 形式 (EPUB / PDF / MOBI) と Media Mix 形式 (manga / audio_drama / video など) を選択
5. **Generate Asset Pack** ボタンを押す
6. 成功すると `asset_id` と `task_id` が表示される
7. **Prepare download** ボタンを押すと Blob URL が生成される
8. **⬇ Download ZIP** リンクをクリックしてダウンロード

## トラブルシューティング

### 503 が出る

`ENABLE_MULTIMEDIA` フラグが無効です。`.env` で `ENABLE_MULTIMEDIA=true` を設定し、サーバを再起動してください。

### EPUB / PDF が生成されない

`ebooklib` / `reportlab` がインストールされていない環境では JSON フォールバックが出力されます。
```
pip install ebooklib reportlab
```
で本物の EPUB/PDF を生成できます。

### 404 (not found)

指定した `asset_id` が存在しません。`GET /multimedia/artifacts/{asset_id}` で確認してください。
