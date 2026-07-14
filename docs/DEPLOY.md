# アプリケーションデプロイ手順

本プロジェクトは Docker で構成済みです。以下に本番環境へのデプロイ手順を示します。

## 1. Docker イメージのビルド

```bash
docker build -t autonovel:latest .
```

## 2. コンテナ起動

```bash
docker run -d \
  --name autonovel \
  -p 8000:8000 \
  -e CORS_ORIGINS=http://my-frontend.com \
  -e API_KEY=YOUR_API_KEY \
  autonovel:latest
```

- `-p 8000:8000`：FastAPI サーバーを外部に公開。
- `-e CORS_ORIGINS`：許可するオリジン。
- `-e API_KEY`：バックエンドサービスのキー。

## 3. フロントエンドビルド

```bash
# フロントエンドディレクトリへ移動
cd frontend
npm ci
npm run build
```

生成された `frontend/dist` ディレクトリをサーバーの静的ファイルとして提供します。

## 4. 静的ファイルの提供

FastAPI の `StaticFiles` を使って以下のように設定します。

```python
# main.py
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

## 5. 監視と自動再起動

Docker Compose を使って設定を簡略化できます。

```yaml
# docker-compose.yml
version: "3"
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=http://my-frontend.com
      - API_KEY=YOUR_API_KEY
    volumes:
      - .:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000
```

## 6. CI/CD の構成（例：GitHub Actions）

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [ main ]
jobs:
  build_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v3
        with:
          tags: ghcr.io/${{ github.repository }}:latest
          push: true
      - name: Deploy to server
        run: |
          ssh user@your-server "docker pull ghcr.io/${{ github.repository }}:latest && docker run -d ..."
```

---

## 追跡可能な変更
- `docker-compose.yml` で確認済み。
- `frontend/dist` は `gitignore` に追加。