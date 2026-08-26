# Docker経由フロントエンドビルド検証計画

## 目的
Dockerを使用してReactフロントエンドのTypeScriptコンパイルとViteビルドを検証。ローカルnpm/node environmentの問題を回避。

---

## 前提条件

- Dockerが利用可能（ソケットアクセス許可されている必要があります）
- Docker compose（v2+）が利用可能

---

## 実行ステップ

### Step 1: TypeScriptコンパイルのみの検証（ビルド前）
```bash
# Nodeのベースイメージを使用してts-decorators互換性を確認
cd I:\autonovel\autonovel

docker run --rm -v "$(pwd)/frontend:/app" -w /app node:20-alpine \
  sh -c "npm --version && node --version && npx tsc --version"

# TypeScriptコンパイル（エラーなし）
# TypeScriptコンパイル（エラーなし）
docker build --target builder -t kaku-frontend-builder ./frontend | tail -20

# TypeScriptコンパイルのみ（ビルドコマンドをスキップ）
# | head -30
```

### Step 2: フルビルド（`npm run build`）の実行
```bash
# 1. バイナリをビルド（拡張) - オプション時のみ
# * 以下のみに焦点を当てる:
# - base stage: コンパイルとビルド
# - builder stage: npm installとnpm run build

# shortcut: src/backend/server.py:6行目
# のパラメータを使用してbuilderステージを直接ビルド

docker build --target builder -t kaku-frontend-builder ./frontend

# コンテナ内で実行してビルドログを確認（オプション）
# docker run --rm --entrypoint sh kaku-frontend-builder \
#   -c "ls -la dist/ && ls -la ." 2>/dev/null || echo "dist フォルダが生成されなかった"
```

### Step 3: ビルド成果物検証
```bash
# コンテナ内でdist/の内容を直接確認
cd I:\autonovel\autonovel

# dist/ディレクトリが存在し、期待される構造を含むことを確認します。
docker run --rm kaku-frontend-builder sh -c "
  echo '=== ビルド成果物チェック ==='
  test -d dist && echo '✓ dist/ フォルダが存在する'
  test -f dist/index.html && echo '✓ dist/index.html が存在する'
  test -d dist/assets && echo '✓ dist/assets/ フォルダが存在する'
  echo '=== 型チェックエラー ==='
  cat /tmp/tsc.log 2>/dev/null || echo 'ログなし'
"
```

### Step 4: フロントエンド Dev サーバーの起動（オプション）
```bash
# クイックな動作確認のために、フロントエンド開発サーバーを起動
# docker compose up -d frontend-dev

# または、コンソールで起動して確認する:
# docker compose up --build frontend-dev
```

### Step 5: 完全な `docker compose` ビルド検証
```bash
# バックエンドとフロントエンドの完全なビルドを実行
cd I:\autonodel\autonovel

docker compose build --parallel

# 全サービスが起動していることを確認（バックエンドはヘルスチェックで待機）
# docker compose ps

# Webサーバーの動作確認（axiosやfetchを使用したリクエストを通じたフロントエンドの動作確認）
# サンプル curl 呼び出し:
# curl -s http://localhost:5173/  # React のエイリアップ出し画面
```

---

## 成功指標

| 検証 | 確認すべき内容 | 成功条件 |
|------|--------------|----------|
| TypeScriptコンパイル | エラーなし（.ts fileの構文） | ✅ exit code=0 |
| Viteビルド | *.js, *.cssなどの出力 | ✅ dist/assets/*.js が存在する |
| HTML生成 | index.html が生成される | ✅ dist/index.html が存在する |
| エントリーポイント | React Routerルートが表示される | ✅ HealthGate表示（ローカライズ） |
| バックエンドとの通信 | `/api/health` などで通信 | ✅ エラーなし（curlを使用） |

---

## トラブルシューティング

### TypeScriptビルドエラー
1. `docker compose up frontend-dev` を使用してnode_modulesディレクトリが新しいコンテナ内にあることを確認
2. 数分かってもビルドが失敗する場合は、エラージャックを直接ログに確認
3. 値上げが可能の場合、cacheを追加:
   ```bash
   docker build --target base -t frontend-base ./frontend
   ```

### 許可エラー
```bash
# 問題が発生した場合は、Windowsの場合は `docker run --privileged` を使用するか:
# Linux/Mac の場合は、`docker buildx` を使用して異なる経路を試してください。
```

### ポート競合
バックエンドをローカルで実行していないことを確認:
```bash
# 両方を実行した場合:
# バックエンド:
#   docker compose up backend
# フロントエンド開発:
#   docker compose up frontend-dev
# 競合を避けるためにサービスを停止:
#   docker compose down
```

---

## 最終確認

```bash
cd I:/autonovel/autonovel

# TypeScriptタイプチェックのみ（このプロジェクトではほとんど必要ありません）
docker run --rm kaku-frontend-builder \
  sh -c "node node_modules/typescript/lib/cli.js --noEmit" 2>&1 | grep -E "error TS|error pronto"

# vite build を実行したか確認する(cmd で確認することが多いです。一般的にdist/index.htmlが存在する必要があります)
ls -la frontend/dist/

# 一時的なログを確認(それでも現在は型チェックlogsが存在する可能性はありません)
cat node_modules/.cache/tsc.log | head -30 2>/dev/null || echo "tscログなし"

# 成功ケース
if [ -f "frontend/dist/index.html" ]; then
  echo "✓ React フロントエンドビルド成功！"
  echo "✓ ビルド出力:
$(ls -la frontend/dist/)"
fi
```

---

## まとめ

1. **docker compose up frontend-dev** を使用してNode environmentの問題を回避
2. **builder stage** を使用してTypeScriptコンパイルとViteビルドを実行（`npm run build` と同じ機能）
3. 生成された `dist/` フォルダを検証
4. オプションでフルデプロイ手順（backend + frontend-dev）をローカルで実行

この計画では、ローカルnpm/nodeインストールを回避し、Dockerファイルを使用してフロントエンドの完全な検証を実現します。