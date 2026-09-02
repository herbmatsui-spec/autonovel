# Multimedia 機能ドキュメント

AutoNovel の Phase 7 マルチメディア展開 (Asset Pack / Media Mix / IF Routes / eBook Export) に関するドキュメント。

## 有効化手順

1. `.env` に `ENABLE_MULTIMEDIA=true` を追加
2. 必要に応じて `ENABLE_AUDIO_SYNTH=true` も追加
3. `bash scripts/dev_multimedia.sh` で開発サーバを起動
4. `GET /health` でルータが登録されたか確認

## ステージング環境デプロイ手順

1. `ENABLE_MULTIMEDIA=true` を `.env` に設定
2. `docker compose up -d backend frontend` で再起動
3. `curl http://localhost:8200/health` で 200 を確認
4. `curl http://localhost:8200/multimedia/tasks/dummy` が 404 (not found) を返すことを確認 (ルータ登録済み)

## カナリアリリース

- 10% トラフィックから開始
- `/metrics` の `multimedia_requests_total` を Grafana で監視
- 5xx エラー率 > 5% でアラート発火

## API エンドポイント一覧

| メソッド | パス | 概要 |
| --- | --- | --- |
| POST | `/multimedia/media-mix` | 漫画/音声ドラマ/動画用台本の生成 |
| POST | `/multimedia/ebook` | EPUB/PDF/MOBI の電子書籍エクスポート |
| POST | `/multimedia/if-routes` | IFルートグラフの生成 |
| POST | `/multimedia/asset-pack` | 統合アセットパック (ZIP) の生成 |
| GET | `/multimedia/artifacts/{asset_id}` | 成果物メタデータ取得 |
| GET | `/multimedia/artifacts/{asset_id}/download` | 成果物ファイルダウンロード |
| GET | `/multimedia/tasks/{task_id}` | タスクステータス取得 |
| GET | `/multimedia/files/{filename}` | 静的ファイル配信 |

## フロント UI

- `frontend/src/components/AssetPackPanel.tsx` を参照
- スタジオワークスペースの「Multimedia」タブから操作

## スクリーンショット

TODO: スクショを `docs/images/multimedia/` に追加する
