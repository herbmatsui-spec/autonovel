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

## 商用EPUB 3 挿絵・口絵の仕様と登録API (Step 47)

### 挿絵仕様概要
- **規格適合性**: EPUB 3.2 / IDPF 規格完全準拠（Kindle縦書き・右開き `page-progression-direction="rtl"` 対応）。
- **対応画像フォーマット**: JPEG (`image/jpeg`), PNG (`image/png`), WebP (`image/webp`), SVG (`image/svg+xml`)。
- **推奨解像度・アスペクト比**:
  - カラー口絵（Frontmatter）: 縦横比 16:9 または 3:2（推奨解像度: 1600×2560px 等の電子書籍標準）。
  - 章間挿絵（Chapter Inset）: 縦長（3:4 または 9:16）、本文見開き直前に自動挿入。
- **CSS組版**:
  - `p-illustration`: 挿絵専用見開きクラス。本文縦書きスタイルと干渉しないよう横書きボックスとして中央配置。
  - `object-fit: contain; max-height: 90vh;` によるデバイス全画面追従。
  - `illustration-caption`: キャプションの下部センタリング表示。

### 挿絵の自動引き当てと配信
1. `POST /multimedia/ebook` 実行時、DB（`multimedia_artifacts` / `illustrations` テーブル）から該当書籍の画像アセットを自動抽出。
2. 目次（`nav.xhtml`, `toc.ncx`）には挿絵が項目として混入しないよう自動フィルタリング。
3. `POST /multimedia/asset-pack` でのZIPアーカイブ内 `04_電子書籍/` に挿絵入り完全EPUBが同梱されます。

