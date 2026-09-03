# 商用出版API連携ガイド

## 概要

AutoNovelの商用出版機能により、生成された小説を主要なプラットフォームへ直接投稿・更新できます。

## 対応プラットフォーム

| プラットフォーム | 方式 | 状態 | 必要認証 | レート制限 |
|----------------|------|------|----------|------------|
| **小説家になろう** | Selenium | ✅ 実装済み | Email/Password | 10 req/min |
| **カクヨム** | 非公式REST API | ✅ 実装済み | API Token | 30 req/min |
| **楽天Kobo** | 公式OAuth2 API | 🚧 実装済み/要審査 | Client ID/Secret | 60 req/min |
| **Kindle (KDP)** | 公式OAuth2 API | 🚧 実装済み/要審査 | Client ID/Secret/Refresh Token | 30 req/min |

> **注意**: KoboとKindleは公式API利用のため、それぞれのプラットフォームで開発者登録・審査が必要です。

## セットアップ

### 1. 環境変数設定

`.env.example` をコピーして `.env` を作成し、認証情報を設定：

```bash
cp .env.example .env
```

```env
# 小説家になろう
NAROU_EMAIL=your_email@example.com
NAROU_PASSWORD=your_password

# カクヨム (マイページ > 設定 > API設定で取得)
KAKUYOMU_API_TOKEN=your_api_token
KAKUYOMU_USER_ID=your_user_id

# 楽天Kobo (開発者ポータルで取得)
KOBO_CLIENT_ID=your_client_id
KOBO_CLIENT_SECRET=your_client_secret

# Amazon KDP (LWA認証フローで取得)
KINDLE_CLIENT_ID=your_client_id
KINDLE_CLIENT_SECRET=your_client_secret
KINDLE_REFRESH_TOKEN=your_refresh_token
KINDLE_MARKETPLACE_ID=A1VC38T7YXB528  # 日本
```

### 2. 依存パッケージインストール

```bash
# なろう用 (Selenium)
pip install selenium webdriver-manager

# 他プラットフォーム用 (HTTPクライアント)
pip install httpx cryptography keyring
```

### 3. ChromeDriver設定 (なろうのみ)

SeleniumがChromeDriverを自動管理します。初回実行時に自動ダウンロードされます。

## 使い方

### API経由での投稿

#### 1. パイプライン実行時に投稿 (新規生成+投稿)

```bash
curl -X POST http://localhost:8200/commercial/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "series_config": {
      "keywords": "ファンタジー,冒険",
      "target_eps": 10,
      "platforms": ["narou", "kakuyomu"]
    },
    "samples": [],
    "platforms": ["narou", "kakuyomu"],
    "do_publish": true
  }'
```

#### 2. 既存書籍の投稿

```bash
curl -X POST http://localhost:8200/commercial/publish \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1,
    "platforms": ["narou", "kakuyomu"],
    "episode_range": [1, 5]
  }'
```

#### 3. 投稿ステータス確認

```bash
curl -X POST http://localhost:8200/commercial/publish/status \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1,
    "platform": "kakuyomu",
    "post_id": "work_123"
  }'
```

#### 4. 投稿履歴取得

```bash
curl -X GET http://localhost:8200/commercial/publish/records/1 \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### 5. 対応プラットフォーム一覧

```bash
curl -X GET http://localhost:8200/commercial/publish/platforms \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Python SDK経由での投稿

```python
from src.backend.workflows.commercial_pipeline import CommercialPipeline
from src.services.publishers import get_credential_store, NarouCredentials

# 認証情報取得
store = get_credential_store()
credentials = {"narou": store.get("narou")}

# パイプライン実行
pipeline = CommercialPipeline()
result = await pipeline.run(
    series_config={
        "keywords": "ファンタジー,冒険",
        "target_eps": 5,
        "platforms": ["narou"]
    },
    samples=[],
    platforms=["narou"],
    credentials=credentials,
    do_publish=True
)

print(result["publish_results"])
```

## 定期投稿スケジュール

連載作品の次話自動投稿をスケジュールできます（開発中）：

```json
{
  "book_id": 1,
  "platforms": ["kakuyomu"],
  "schedule": {
    "interval_days": 7,
    "start_at": "2026-01-15T19:00:00+09:00",
    "timezone": "Asia/Tokyo"
  }
}
```

## アーキテクチャ

### PublisherAdapter パターン

```
BaseExporter (フォーマット) ←独立→ PublisherAdapter (投稿)
```

- **Exporter**: プラットフォーム別テキスト整形
- **PublisherAdapter**: 実API通信・認証・投稿・更新

### クラス構造

```
src/services/publishers/
├── base.py          # 基底クラス・例外・リトライ
├── narou.py         # Selenium実装
├── kakuyomu.py      # REST API実装
├── kobo.py          # OAuth2実装
├── kindle.py        # OAuth2実装
├── credentials.py   # 認証情報管理
└── __init__.py      # レジストリ・ファクトリ
```

### データフロー

```
1. CommercialPipeline.run()
   ↓
2. Bible生成 → コンテンツ生成
   ↓
3. _publish_to_platforms()
   ├── Publisher取得 (get_publisher)
   ├── 認証
   ├── 第1話: publish()
   ├── 第2話以降: update_chapter(post_id)
   └── post_idをEpisodeに記録
   ↓
4. PublishRecordに永続化
```

## トラブルシューティング

### よくあるエラー

| エラー | 原因 | 対処 |
|--------|------|------|
| `AuthError: 認証失敗` | 認証情報不正/期限切れ | `.env`確認、トークン再取得 |
| `RateLimitError` | API呼び出し過多 | `rate_limit`設定調整、待機 |
| `NetworkError` | 接続失敗 | ネットワーク/プロキシ確認 |
| `ValidationError` | 文字数超過等 | コンテンツ確認・調整 |
| `ModuleNotFoundError: webdriver_manager` | 依存不足 | `pip install webdriver-manager` |

### なろう固有の問題

- **ChromeDriverバージョン不一致**: `webdriver-manager`が自動解決
- **ヘッドレスモードで動作しない**: `--headless=new`オプション確認
- **ログインページ構造変更**: セレクタ更新が必要

### カクヨム固有の問題

- **APIエンドポイント変更**: 非公式APIのため要確認
- **APIトークン期限切れ**: 設定画面で再生成

## 設定ファイル

`config/publishers.yaml` でプラットフォーム別設定を管理：

```yaml
narou:
  enabled: true
  rate_limit:
    per_minute: 10
    per_hour: 100
  selenium:
    headless: true
    timeout: 30

kakuyomu:
  enabled: true
  api_base: "https://api.kakuyomu.jp/v1"
  rate_limit:
    per_minute: 30
```

## セキュリティ

- 認証情報は環境変数・キーリング・暗号化ファイルの優先順位で管理
- 暗号化にはFernet (AES-128) を使用
- キーファイルは `~/.autonovel/credential.key` に保存 (600パーミッション)

## 開発者向け: 新プラットフォーム追加

1. `src/services/publishers/new_platform.py` 作成
2. `PublisherAdapter` を継承し、4メソッド実装:
   - `authenticate()`
   - `publish()`
   - `update_chapter()`
   - `get_post_status()`
3. `__init__.py` の `_PUBLISHERS` に登録
4. `credentials.py` の `ENV_MAPPING` に環境変数追加
5. テスト作成: `tests/unit/publishers/test_new_platform.py`