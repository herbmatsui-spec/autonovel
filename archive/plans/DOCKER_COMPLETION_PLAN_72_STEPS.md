# 未実装・未完了部分の詳細実装計画書（Docker 活用版）

**生成日:** 2026-07-23
**前提:**
- ローカルの `npm install` / `tsc` 解決問題は **Docker コンテナ内で完結** させる方針
- 既存 `frontend/Dockerfile` はマルチステージ構成（`dev` / `builder` / `production`）で内部で `npm install --legacy-peer-deps` を実行済み
- `docker-compose.yml` は `backend`（`:8200`）と `frontend`（`:3000`）の2サービス構成

**現状の未完了項目:**
1. `npm run build` が通らない問題（`tsc` 未解決）の解決
2. ブラウザでの主要フロー確認
3. バックエンド CORS 設定見直し（任意）

---

## 方針: Docker で完結させる理由

ローカル環境（Windows + PowerShell）では以下の問題が発生していた:
- `npm install --legacy-peer-deps` を実行しても `node_modules/typescript` が生成されない
- 結果として `npm run build` が `tsc not recognized` で失敗する

これらはローカル PATH / 権限 / npm キャッシュ等の環境起因と考えられるため、**Node 20 イメージ上で一貫して動く Docker を検証・実行環境として採用する**。これにより低性能 LLM でも「コマンド1つで実行 → 成否判定」の小さなステップに分解できる。

---

## Phase A: Docker によるビルド検証（ステップ1-12）

### グループA1: Docker 環境確認（ステップ1-4）

**ステップ1: Docker / Docker Compose 可用性確認**
```bash
docker --version
docker compose version
```
期待結果: Docker 24+ / Compose v2+ が応答

**ステップ2: 現在の docker-compose.yml 内容確認**
```bash
cat docker-compose.yml
```
確認点:
- `backend` サービスが `:8200` を公開
- `frontend` サービスが `:3000` を公開
- Streamlit サービスは削除済み

**ステップ3: frontend/Dockerfile のステージ確認**
```bash
cat frontend/Dockerfile
```
確認点:
- `base` ステージ: `npm install --legacy-peer-deps --no-audit --no-fund`
- `dev` ステージ: `npm run dev --host 0.0.0.0`（`:5173`）
- `builder` ステージ: `npm run build`（成果物生成）
- `production` ステージ: nginx で `:3000` 公開

**ステップ4: バックエンド Dockerfile 確認**
```bash
cat Dockerfile
```
確認点（既に修正済み）:
- `EXPOSE 8200`（8501 削除済み）
- `requirements.txt` から `streamlit` が削除されているか確認

### グループA2: Docker ビルド実行（ステップ5-8）

**ステップ5: backend イメージのみビルド**
```bash
docker compose build backend
```
期待結果: 成功。失敗時は `requirements.txt` の `streamlit` 依存削除が必要

**ステップ6: requirements.txt から streamlit を削除（必要な場合のみ）**
```bash
grep -n streamlit requirements.txt
```
存在する場合:
```
# requirements.txt から以下のような行を削除
streamlit==...
streamlit-*...
```
削除後、`python -m pip install` 相当は Docker ビルドで再実行される

**ステップ7: frontend イメージのビルド（builder ステージ検証）**
```bash
docker compose build frontend
```
期待結果: 成功。`tsc -p tsconfig.app.json && vite build` が Docker 内で完結
失敗時の出力例:
- `tsc: command not found` → base ステージの `npm install` 失敗の可能性
- 型エラー → `frontend/src/` の TS エラー修正が必要

**ステップ8: ビルド失敗時のログ確認**
```bash
docker compose build frontend --progress plain 2>&1 | tee logs/frontend_build.log
```
`logs/frontend_build.log` を確認し、失敗箇所を特定

### グループA3: ビルド成果物確認（ステップ9-12）

**ステップ9: ビルド済み dist の存在確認**
```bash
docker compose run --rm frontend ls -la dist
```
期待結果: `dist/index.html`, `dist/assets/` が生成済み

**ステップ10: バックエンド依存の整合性確認**
```bash
docker compose run --rm backend python -c "import src.backend.server; print('OK')"
```
期待結果: `OK`

**ステップ11: 既存テストの Docker 実行確認**
```bash
docker compose run --rm frontend npm run test:run
```
期待結果: `api.test.ts` のモックテストが全て PASS
失敗時は `frontend/src/test/api.test.ts` と `frontend/src/api.ts` の不一致を確認

**ステップ12: ビルド成果物のサニティ確認**
```bash
docker compose run --rm frontend sh -c "ls dist/assets/*.js | head -3"
```
期待結果: ハッシュ付き JS が生成済み

---

## Phase B: Docker による起動・動作確認（ステップ13-24）

### グループB1: コンテナ起動（ステップ13-16）

**ステップ13: 全サービス起動（バックグラウンド）**
```bash
docker compose up -d
```
期待結果: `backend` と `frontend` が起動

**ステップ14: 起動状態確認**
```bash
docker compose ps
```
期待結果: 両サービス `healthy` または `running`

**ステップ15: backend ヘルスチェック**
```bash
curl -s http://localhost:8200/health | jq .
```
期待結果: `"status": "healthy"` 等

**ステップ16: frontend 配信確認**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```
期待結果: `200`

### グループB2: 主要フロー確認（ステップ17-20）

**ステップ17: ブラウザで React UI 表示確認**
- URL: http://localhost:3000
- 確認点: ランディング、サイドバー、APIキー入力欄の表示

**ステップ18: API キー入力 → 作品一覧取得**
- サイドバーから API キー入力
- `BooksTab` で `/api/books` 一覧取得を確認
- ネットワークタブで `200` 応答を確認

**ステップ19: かんたんモード生成フロー**
- `EasyModeDialog` でジャンル等入力 → 「生成開始」
- `TaskMonitor` に SSE 進捗表示されることを確認
- `/api/tasks/{id}/stream` が接続されることを確認

**ステップ20: 執筆フロー確認**
- `WriteTab` で執筆範囲入力 → 「執筆開始」
- `TaskMonitor` 進捗 + リアルタイムプレビュー表示
- 完了後、章一覧が更新されることを確認

### グループB3: バックエンド連携確認（ステップ21-24）

**ステップ21: プロット拡張フロー**
- `PlotsTab` → 「プロット全話自動展開」
- `/api/plots/expand` のタスク起動を確認
- 完了後、プロット一覧が表示されることを確認

**ステップ22: 品質分析フロー**
- `AnalyticsTab` → 「分析エンジン起動」
- `/api/critique/optimize` のタスク起動を確認
- 監査履歴が表示されることを確認

**ステップ23: 監査タブ確認**
- `AuditTab` で Issue 一覧取得
- `/api/issues/books/{id}` の応答を確認
- 「AIクイック修正」実行で `/api/issues/{id}/resolve` が呼ばれることを確認

**ステップ24: 文体ラボ確認**
- `StyleLabTab` でサンプル入力 → 「分析開始」
- `/api/marketing/analyze_style_dna` の応答を確認
- 結果 JSON が表示されることを確認

---

## Phase C: DEV サービス追加（ステップ25-36）

### グループC1: docker-compose に dev プロファイル追加（ステップ25-28）

現在の `docker-compose.yml` は `frontend` サービスが `:3000`（本番 nginx）を公開。
開発時は Vite HMR（`:5173`）を使えるよう、`dev` プロファイルを追加する。

**ステップ25: docker-compose.yml に dev サービス追加**
```yaml
# docker-compose.yml に追加
  frontend-dev:
    profiles:
      - dev
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: dev
    container_name: kaku_frontend_dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8200/api
    depends_on:
      backend:
        condition: service_healthy
```

**ステップ26: dev プロファイル起動確認**
```bash
docker compose --profile dev up frontend-dev
```
期待結果: Vite dev サーバーが `:5173` で起動

**ステップ27: Vite HMR 動作確認**
- `frontend/src/App.tsx` を編集
- ブラウザ（http://localhost:5173）で即時反映を確認

**ステップ28: dev サービス停止**
```bash
docker compose --profile dev down
```

### グループC2: テスト実行環境整備（ステップ29-32）

**ステップ29: frontend テスト実行コマンド整備**
```bash
docker compose run --rm frontend npm run test:run
```
期待結果: `vitest run` で全テスト PASS

**ステップ30: テスト失敗時の対処**
`api.test.ts` で import している以下が `api.ts` に存在するか確認:
- `runCommercialPipeline` → 存在しない場合は追加が必要
- `refineErotic` → 存在しない場合は追加が必要

**ステップ31: 不足 API 関数の追加（必要な場合）**
`frontend/src/api.ts` に追加:
```typescript
export async function runCommercialPipeline(params: any): Promise<any> {
  return apiRequest(`${API_BASE_URL}/commercial/run`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function refineErotic(params: any): Promise<any> {
  return apiRequest(`${API_BASE_URL}/refine_erotic`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
```

**ステップ32: テスト再実行**
```bash
docker compose run --rm frontend npm run test:run
```
期待結果: 全テスト PASS

### グループC3: 型チェック分離（ステップ33-36）

**ステップ33: 型チェック専用コマンド確認**
`frontend/package.json` に以下を追加（必要な場合）:
```json
{
  "scripts": {
    "typecheck": "tsc -p tsconfig.app.json --noEmit"
  }
}
```

**ステップ34: Docker 内で型チェック実行**
```bash
docker compose run --rm frontend npm run typecheck
```
期待結果: エラー0件

**ステップ35: 型エラー修正（必要な場合）**
出力された TS エラーを1件ずつ修正:
- 未使用 import の削除
- 型注釈の追加
- `any` → 具体型への置換（必要最小限）

**ステップ36: 型チェック再実行でクリーン確認**
```bash
docker compose run --rm frontend npm run typecheck
```
期待結果: エラー0件

---

## Phase D: バックエンド依存整理（ステップ37-48）

### グループD1: requirements.txt 整理（ステップ37-40）

**ステップ37: requirements.txt の streamlit 依存確認**
```bash
grep -in streamlit requirements.txt
```
存在する場合、以下のような行を特定:
```
streamlit==1.x.x
streamlit-aggrid==...
```

**ステップ38: streamlit 関連パッケージ削除**
`requirements.txt` から streamlit で始まる行を全て削除:
```bash
# 手動編集または以下のコマンド
sed -i '/^streamlit/d; /^streamlit-/d' requirements.txt
```

**ステップ39: バックエンド再ビルドで依存解決確認**
```bash
docker compose build backend
```
期待結果: 成功

**ステップ40: バックエンド起動で import エラー確認**
```bash
docker compose up backend -d
docker compose logs backend --tail 50
```
期待結果: `streamlit` 関連の ImportError なし

### グループD2: バックエンドソースの streamlit 参照確認（ステップ41-44）

**ステップ41: src/ 内の streamlit 参照検索**
```bash
grep -rn "import streamlit\|from streamlit" src/ --include="*.py"
```
期待結果: 0件（0件なら OK）

**ステップ42: streamlit_app/ への参照検索**
```bash
grep -rn "from streamlit_app\|import streamlit_app" src/ --include="*.py"
```
期待結果: 0件。存在する場合は `streamlit_app/` 削除の影響があるため修正が必要

**ステップ43: 参照残存箇所の修正**
見つかった箇所を1つずつ修正:
- `streamlit_app.api_client` の代替実装を `src/infrastructure/` 等に移設
- または該当 import を削除し、React API 経由に切り替え

**ステップ44: バックエンド起動で回帰確認**
```bash
docker compose restart backend
docker compose logs backend --tail 30
```
期待結果: エラーなしで起動

### グループD3: スクリプト・バッチ整理（ステップ45-48）

**ステップ45: 起動バッチファイルの streamlit 参照確認**
```bash
grep -l streamlit *.bat *.sh 2>/dev/null
```
対象: `start_app.bat`, `start_app.sh`, `run_app.bat`, `アプリ起動.bat` 等

**ステップ46: バッチファイルから streamlit 起動行削除**
該当ファイルから以下のような行を削除:
```
streamlit run streamlit_app/app.py ...
start streamlit run ...
```
React dev server 起動行に置き換え:
```
cd frontend && npm ci && npm run dev
```
または Docker 版:
```
docker compose up -d
```

**ステップ47: テストスクリプトの streamlit 参照確認**
```bash
grep -rn streamlit tests/ --include="*.py"
```
存在する場合は該当テストを削除または React API テストへ移行

**ステップ48: CI ワークフロー確認**
```bash
cat .github/workflows/ci.yml
```
`streamlit run` や `streamlit_app/` 参照がないか確認。あれば削除

---

## Phase E: CORS 設定見直し（ステップ49-60）

### グループE1: 現状確認（ステップ49-52）

**ステップ49: バックエンド CORS 設定確認**
```bash
grep -rn "allow_origins\|CORSMiddleware" src/ --include="*.py"
```
対象ファイル: `src/backend/server.py` 等

**ステップ50: CORS 許可 origin 一覧確認**
現在の `allow_origins` 値を確認:
- `["*"]` → 要修正
- 環境変数対応済み → 確認のみ

**ステップ51: .env.example の CORS 設定確認**
```bash
cat .env.example
```
`CORS_ALLOWED_ORIGINS` の行があれば、`http://localhost:8501` が残っていないか確認

**ステップ52: CORS 許可 origin 整理**
許可 origin を以下に整理:
- 開発: `http://localhost:5173`（Vite dev）, `http://localhost:3000`（Docker prod）
- `http://localhost:8501`（Streamlit）は削除

### グループE2: CORS 設定修正（ステップ53-56）

**ステップ53: server.py の CORS を環境変数駆動に統一**
```python
# src/backend/server.py
import os
allowed = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in allowed.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**ステップ54: .env.example 更新**
```
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

**ステップ55: docker-compose.yml に CORS 環境変数追加**
```yaml
backend:
  environment:
    - CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

**ステップ56: バックエンド再ビルド・起動確認**
```bash
docker compose build backend
docker compose up backend -d
```

### グループE3: CORS 動作確認（ステップ57-60）

**ステップ57: 許可 origin からのリクエスト確認**
```bash
curl -I -X OPTIONS http://localhost:8200/api/books \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"
```
期待結果: `Access-Control-Allow-Origin: http://localhost:3000` が応答

**ステップ58: 不許可 origin からの拒否確認**
```bash
curl -I -X OPTIONS http://localhost:8200/api/books \
  -H "Origin: http://evil.example.com"
```
期待結果: `Access-Control-Allow-Origin` ヘッダなし

**ステップ59: dev プロファイルでの CORS 確認**
```bash
docker compose --profile dev up frontend-dev -d
curl -I http://localhost:5173
```
期待結果: Vite プロキシ経由で `/api` が `200`

**ステップ60: フロントエンドから API 呼び出し総合確認**
ブラウザで http://localhost:5173 を開き:
- API キー入力 → 作品一覧取得
- CORS エラーが出ないことを確認

---

## Phase F: 最終統合確認（ステップ61-72）

### グループF1: 全体ビルド・起動（ステップ61-64）

**ステップ61: 全サービス再ビルド**
```bash
docker compose build
```
期待結果: backend, frontend 共に成功

**ステップ62: 全サービス起動**
```bash
docker compose up -d
```

**ステップ63: 起動状態・健全性確認**
```bash
docker compose ps
docker compose logs --tail 30
```
期待結果: 全サービス healthy

**ステップ64: エンドツーエンド smoke 確認**
```bash
# バックエンド
curl -s http://localhost:8200/health | jq .status
# フロントエンド
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```
期待結果: 両方 `200` / `healthy`

### グループF2: 機能回帰テスト（ステップ65-68）

**ステップ65: かんたんモード全自動フロー確認**
- http://localhost:3000 で API キー入力
- EasyModeDialog → 生成開始
- TaskMonitor で進捗 → 完了
- 章一覧に成果物反映を確認

**ステップ66: 上級者モード各 Tab 確認**
- PlanningTab → 企画生成
- PlotsTab → プロット拡張
- WriteTab → 執筆
- AnalyticsTab → 分析
- AuditTab → Issue 解決
- StyleLabTab → 文体分析

**ステップ67: エラーハンドリング確認**
- API キー未入力での操作 → 警告 Toast 表示
- バックエンド停止時 → `HealthGate` 表示
- タスク失敗時 → エラー Toast 表示

**ステップ68: ログ・エラー確認**
```bash
docker compose logs --tail 100 | grep -i error
```
期待結果: 重大エラーなし

### グループF3: ドキュメント・設定最終調整（ステップ69-72）

**ステップ69: README の Docker 起動手順確認**
```bash
grep -n "docker compose" README.md
```
手順が `docker compose up --build` のみで完結するか確認

**ステップ70: 進捗レポート更新**
`plans/STREAMLIT_TO_REACT_MIGRATION_STATUS.md` の未完了項目に完了マーク:
- [x] Docker による `npm run build` 検証
- [x] ブラウザでの主要フロー確認
- [x] CORS 設定見直し

**ステップ71: 削除前最終バックアップ確認**
```bash
ls -la backup/streamlit_app_backup/ | head -5
ls -la backup/frontend_src_backup/ | head -5
```
バックアップが健在であることを確認

**ステップ72: 完了宣言と次ステップ記録**
`plans/STREAMLIT_TO_REACT_MIGRATION_STATUS.md` に完了日付を記録:
```
**状態:** React 移行完了 / Streamlit 完全廃止 / Docker 検証完了
**完了日:** 2026-07-23
```

---

## 72ステップ総括表

| Phase | ステップ | 主要タスク |
|-------|---------|-----------|
| Phase A | 1-12 | Docker によるビルド検証 |
| Phase B | 13-24 | Docker による起動・動作確認 |
| Phase C | 25-36 | DEV サービス追加・テスト整備 |
| Phase D | 37-48 | バックエンド依存整理 |
| Phase E | 49-60 | CORS 設定見直し |
| Phase F | 61-72 | 最終統合確認 |

---

## 注意事項

1. **各ステップは小さく・自己完結**: 1ステップ = 1コマンド or 1ファイル編集
2. **失敗時は次に進まない**: エラーログを確認してから次ステップへ
3. **Docker を唯一の実行環境とする**: ローカル npm に依存しない
4. **バックアップは保持**: `backup/` は最終確認まで消去しない
5. **ステップ30, 31 は条件付き**: `runCommercialPipeline` / `refineErotic` が `api.ts` に既存すれば不要

---

## 参照ファイル

- `docker-compose.yml`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `frontend/vite.config.ts`
- `frontend/src/test/api.test.ts`
- `plans/STREAMLIT_TO_REACT_MIGRATION_STATUS.md`
- `plans/STREAMLIT_TO_REACT_MIGRATION_72_STEPS.md`