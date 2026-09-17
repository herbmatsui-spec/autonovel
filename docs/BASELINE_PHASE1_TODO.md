# フェーズ1（コア救命）実装タスクリスト & ベースライン

本ドキュメントは、フェーズ0（止血と身軽化）の完了を経て確定した、フェーズ1（コア救命・重要バグ修正）の優先修正タスクリストです。

---

## 🚨 P0: 最優先・致命的不具合（即死バグ）

### 1. Stripe 決済 Webhook 500 クラッシュの修正
- **対象ファイル**: `src/backend/routers/billing_webhook.py`
- **症状**: `'coroutine' object has no attribute 'id'`（非同期関数の await 漏れ）
- **影響**: ユーザーが課金してもクレジットが付与されず、Webhook がエラー応答する商用致命傷。
- **対応方針**: 非同期DBセッション・Stripe呼び出し箇所の await を補完し、`tests/unit/services/test_stripe_payment.py` を通過させる。

### 2. LangGraph 執筆ワークフロー Checkpointer エラーの修正
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **症状**: `Checkpointer requires one or more of the following 'configurable' keys: thread_id, checkpoint_ns, checkpoint_id`
- **影響**: Studioモードおよび LangGraph 経由の執筆ループが初期化時点で失敗する。
- **対応方針**: StateGraph 実行時の config 引数に `thread_id` などの必須キーを正しく注入し、`tests/unit/workflows/test_writing_graph_flow.py` を通過させる。

---

## ⚠️ P1: 主要コンポーネントのテスト破損修正

### 3. GraphRAG / Apache AGE ハイブリッド検索の修正
- **対象ファイル**: `src/services/graph_pipeline.py`, `src/services/age_client.py`
- **テスト**: `tests/unit/test_graphrag.py`（5件失敗）

### 4. 認証ミドルウェア & RBAC / JWT 修正
- **対象ファイル**: `src/backend/middleware/auth_middleware.py`, `src/backend/security/jwt.py`
- **テスト**: `tests/unit/test_auth_middleware.py`, `tests/unit/test_jwt_security.py`

### 5. 8オーディター差分解析 & フォールバック
- **対象ファイル**: `src/agents/specialists/`
- **テスト**: `test_auditor_actionable_diffs.py`, `test_actionable_diff_parsing.py`

---

## 📊 目標品質指標
- **失敗テスト件数**: 0 件（ALL GREEN）
- **CIステータス**: 全ジョブ PASS（`continue-on-error` なし）
