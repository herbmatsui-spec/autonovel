# React フロントエンド ビルド・検証 未完了タスク詳細計画書

**作成日:** 2026-07-22  
**状態:** 未完了（作業待ち）  
**前提:** Streamlit → React 移行コード変更済み

---

## 残タスク概要

| # | タスク | 優先度 | 状態 |
|---|--------|--------|------|
| A | npm install / npm run build の正常化 | HIGH | 未着手 |
| B | ブラウザで主要フロー確認 | HIGH | 未着手 |
| C | バックエンド CORS 設定確認・最適化 | MEDIUM | 未着手 |

---

## タスクA: npm install / npm run build の正常化

### 問題原因の特定（Step A-1）

**症状:**
- `npm run build` 実行時に `tsc is not recognized` エラー
- `node_modules/.bin/tsc` が存在しない
- `node_modules/typescript/` フォルダが存在しない

**確認コマンド:**
```powershell
# 1. node_modules/.bin の内容確認
cmd.exe /c "dir /b D:\autonovel\autonovel\frontend\node_modules\.bin"

# 2. typescript フォルダ是否存在
cmd.exe /c "if exist D:\autonovel\autonovel\frontend\node_modules\typescript\package.json (echo EXISTS) else (echo MISSING)"

# 3. npm version 確認
cmd.exe /c "npm.cmd --version"

# 4. node version 確認
cmd.exe /c "node --version"
```

### 原因別の解决方案

#### 原因A: npm install が途中で失敗していた（最有力）

**症状:** node_modules は存在するが typescript が入っていない

**解決 Step A-2:**
```powershell
# frontend ディレクトリへ移動
cd D:\autonovel\autonovel\frontend

# node_modules を削除してクリーンインストール
cmd.exe /c "cd /d D:\autonovel\autonovel\frontend && rmdir /s /q node_modules"
cmd.exe /c "cd /d D:\autonovel\autonovel\frontend && npm.cmd install --legacy-peer-deps"
```

**期待結果:** `node_modules/.bin/tsc` が作成される

#### 原因B: npm install が成功しているが PATH が解決されていない

**症状:** tsc は存在するが npm run build が PATH を見つけられない

**解決 Step A-3:**
```powershell
# npm run build を直接 tsc パス指定で実行
cmd.exe /c "cd /d D:\autonovel\autonovel\frontend && npx.cmd tsc -p tsconfig.app.json && npx.cmd vite build"
```

または package.json の build スクリプトを修正:
```json
"build": "node_modules/.bin/tsc -p tsconfig.app.json && node_modules/.bin/vite build"
```

#### 原因C: Windows 環境での npm/node_modules 権限問題

**解決 Step A-4:**
```powershell
# PowerShell を管理者として実行後:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd D:\autonovel\autonovel\frontend
npm.cmd install --legacy-peer-deps
```

### build 成功確認（Step A-5）

```powershell
cd D:\autonovel\autonovel\frontend
npm.cmd run build
```

**期待結果:**
```
> frontend@1.0.0 build
> tsc -p tsconfig.app.json && vite build

vite v5.x.x building for production...
✓ 45 modules transformed.
dist/index.html                  0.46 kB
dist/assets/index-[hash].css    12.34 kB
dist/assets/index-[hash].js     142.56 kB
✓ built in 4.23s
```

### dist フォルダの出力確認（Step A-6）

```powershell
cmd.exe /c "dir /b D:\autonovel\autonovel\frontend\dist"
```

**期待結果:** `index.html`, `assets/` フォルダが存在

---

## タスクB: ブラウザで主要フロー確認

### 前提条件確認（Step B-1）

**バックエンド起動確認:**
```powershell
# バックエンドがポート 8200 で起動しているか確認
curl http://localhost:8200/health
```

**React フロントエンド起動確認:**
```powershell
cd D:\autonovel\autonovel\frontend
npm.cmd run dev
```

期待: `VITE v5.x.x  ready in 500ms` と表示され、`http://localhost:5173` でアクセス可能

### 検証フロー一覧（Step B-2）

#### フロー1: 初期起動〜作品一覧表示
1. ブラウザで `http://localhost:3000` を開く（または `http://localhost:5173`）
2. Health Gate がバックエンド接続を確認
3. サイドバーに API キー入力欄が表示される
4. API キーを入力して確定
5. 作品一覧（BooksTab）が表示される
6. **確認ポイント:** エラーなく作品一覧が読める

#### フロー2: かんたんモード（EasyMode）による新規作品生成
1. 「➕ 新規自動生成 (かんたんモード)」ボタンをクリック
2. EasyModeDialog がモーダル表示
3. ジャンル・キーワード・アーキタイプ・目標話数を入力
4. 「🚀 生成開始」をクリック
5. バックグラウンドタスクが起動し、TaskMonitor パネルが表示
6. **確認ポイント:** タスク進捗がリアルタイムで更新される

#### フロー3: 作品選択〜プロット確認
1. 作品一覧から任意の作品をクリック
2. プロット（PlotsTab）に遷移
3. プロットストーリーラインが表示される
4. **確認ポイント:** 各エピソード毎のタイトル・緊張度が表示

#### フロー4: エピソード執筆
1. 執筆（WriteTab）に遷移
2. WriteForm で話数範囲・情熱度を設定
3. 「✍️ 執筆開始」をクリック
4. TaskMonitor で執筆進捗がリアルタイム表示
5. 完了後、ChapterCard が一覧に追加
6. **確認ポイント:** リアルタイム執筆プレビューが動作

#### フロー5: AI品質分析
1. 分析（AnalyticsTab）に遷移
2. 「🔍 分析エンジン起動」をクリック
3. バックグラウンドタスク起動
4. 監査レポート履歴が追加される
5. **確認ポイント:** 品質分析結果がグラフ・リスト表示される

### 異常系確認（Step B-3）

- APIキー未入力での操作 → エラーメッセージ表示
- 作品未選択でのタブ遷移 → 作品選択促すUI表示
- バックエンド接続失敗時 → HealthGate がエラー表示

---

## タスクC: バックエンド CORS 設定確認・最適化

### 現在のリード時確認（Step C-1）

```python
# D:\autonovel\autonovel\src\backend\server.py の CORS 設定を確認
grep -n "CORSMiddleware\|allow_origins" src/backend/server.py
```

### 現在の設定把握

`src/backend/server.py` の `CORSMiddleware` 設定で `allow_origins` を確認

### 推奨設定（Step C-2）

**開発環境:**
```python
allow_origins=[
    "http://localhost:5173",  # React Dev Server
    "http://localhost:3000",   # React Prod preview
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
```

**本番環境:**
```python
allow_origins=[
    "https://your-production-domain.com",
]
```

### 設定確認テスト（Step C-3）

```powershell
# 許可originからのリクエスト
curl -I -X OPTIONS http://localhost:8200/health -H "Origin: http://localhost:5173"
# → Access-Control-Allow-Origin: http://localhost:5173 が返る

# 不許可originからのリクエスト
curl -I -X OPTIONS http://localhost:8200/health -H "Origin: http://malicious-site.com"
# → Access-Control-Allow-Origin が返らない（または * 以外）
```

---

## 緊急度別優先順位

### 今すぐ対応（HIGH）
1. **A-2: npm install 再実行** - これが全工程のボトルネック
2. **A-5: npm run build 成功確認** - コード変更の検証

### すぐ対応（HIGH）
3. **B-1/B-2: ブラウザ検証** - 主要5フローの動作確認
4. **B-3: 異常系確認** - エラー処理の確認

### 任意対応（MEDIUM）
5. **C-1/C-2: CORS 設定最適化** - 本番前のセキュリティ強化

---

## リスクと対策

| リスク | 発生確率 | 対策 |
|--------|----------|------|
| npm install が ESLint 依存関係で失敗 | 高 | `--legacy-peer-deps` フラグ継続使用 |
| Windows ファイルパス長問題 | 中 | プロジェクトパスを短くする（可能なら） |
| バックエンド未起動によるブラウザ確認失敗 | 低 | 先に `uvicorn src.backend.server:app` を起動 |

---

## 完了条件

- [ ] `npm run build` がエラーなく完了し、`dist/` フォルダが生成された
- [ ] ブラウザで主要5フロー（起動〜作品生成〜執筆〜分析）が動作確認できた
- [ ] CORS 設定が許可リスト形式で設定された（任意）