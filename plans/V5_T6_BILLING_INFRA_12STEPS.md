# AutoNovel v5.0 実装計画書 T6: 課金・クレジット・インフラ健全化 (全12ステップ)

**対象領域**: コア設計 6 (Hybrid Billing, Cost Circuit Breaker & Auth Security)  
**目的**: テキスト執筆（1クレジット/約3円）と画像生成（5クレジット/約15円）のハイブリッド課金を確立し、Stripe Webhookの安定化、コストガードのモック解消、および認証ヘッダー統一を行う。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用可能。  
**リグレッション防止**: 各コード変更ステップでは既存機能のリグレッションテストを作成し、CIパイプラインで自動検証を行う。

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Service | `src/services/cost_budget_guard.py` | [MODIFY] `total_cost_usd = float(book_id) * 0.5` のモックを実DB集計へ置換 |
| **Step 2** | Router | `src/backend/routers/cost.py` | [MODIFY] 作品別コスト取得APIでリアルタイムな予算消化率を返却 |
| **Step 3** | Router | `src/backend/routers/billing_webhook.py` | [MODIFY] Stripeイベント処理内のコルーチン `await` 漏れ修正 |
| **Step 4** | Service | `src/services/billing/credit_service.py` | [MODIFY] テキスト執筆（1pt）、画像生成（5pt）の消費ルール定数化 |
| **Step 5** | Task | `src/backend/tasks/generation_tasks.py` | [MODIFY] セッション管理とクレジット減算の安全性向上 |
| **Step 6** | Test | `tests/unit/billing/test_credit_service_deduct.py` | [NEW] 残高不足・二重消費防止テスト |
| **Step 7** | Client | `frontend/src/api/client.ts` | [CHECK] `apiFetch` のエラーハンドリングと認証トークン付与確認 |
| **Step 8** | Client | `frontend/src/api/graph.ts` | [MODIFY] 生 `fetch` を `apiFetch` に置換（認証ヘッダー保証） |
| **Step 9** | Client | `frontend/src/api/editor.ts` | [MODIFY] 生 `fetch` を `apiFetch` に置換（認証ヘッダー保証） |
| **Step 10** | Client | `frontend/src/components/common/PublishExportModal.tsx` | [MODIFY] 生 `fetch` を `apiFetch` に置換（認証ヘッダー保証） |
| **Step 11** | Script | `scripts/verify_docker_config.py` | [MODIFY] 月額5,000円以内運用の低スペックコンテナ構成検証 |
| **Step 12** | E2E | `tests/integration/test_billing_and_auth_guard.py` | [NEW] 認証保護とクレジット消費のE2Eテスト |

---

## 🛠️ 各ステップ詳細手順

### Step 1: コストガードのモック解消 (`src/services/cost_budget_guard.py`)
- **目的**: 仮の計算式（`float(book_id) * 0.5`）を廃止し、DBの `TokenUsageLog` テーブルから作品別の消費金額（USD）を正確に集計する。
- **実装内容**:
```python
async def check_budget_status_async(self, db_session, book_id: int) -> BudgetStatus:
    # 実際の消費金額をDBから集計
    total_cost = await self.calculator.get_total_cost_for_book(db_session, book_id)
    if self.budget_limit <= 0:
        return BudgetStatus.NORMAL
    ratio = total_cost / self.budget_limit
    if ratio < 0.7:
        return BudgetStatus.NORMAL
    elif ratio < 0.9:
        return BudgetStatus.WARNING
    return BudgetStatus.EXCEEDED
```
- **リグレッション防止**: 
  - 既存のコストガード機能のインターフェースが変更されないことを確認するため、関連するユニットテストを作成または更新
  - モックから実DB集計への変更による動作の差分を検出するためのテストケースを追加
- **検証コマンド**: 
  - `pytest tests/unit/services/test_cost_budget_guard.py`
  - `python -m pytest tests/unit/services/ -k cost_budget_guard -v` (詳細なテスト実行)

---

### Step 2: コストAPI改修 (`src/backend/routers/cost.py`)
- **目的**: `GET /api/cost/budget/{book_id}` で最新の予算比率と、90%超過時のダウングレード状態を正確に返却。
- **検証コマンド**: `python -c "from src.backend.routers.cost import router; print(router)"`
- **リグレッション防止**: 
  - 既存のコストAPIのエンドポイント仕様が変更されないことを確認するため、API契約テストを作成
  - レスポンスフォーマットとステータスコードの互換性を維持するためのテストケースを追加
- **検証コマンド追加**: `python -m pytest tests/unit/routers/test_cost.py -v`

---

### Step 3: Webhook `await` 漏れ修正 (`src/backend/routers/billing_webhook.py`)
- **目的**: `handle_checkout_session_completed` 内で非同期DB更新関数が同期呼び出しされてクラッシュする不具合を修正。
- **検証コマンド**: `pytest tests/unit/routers/test_billing_webhook.py`
- **リグレッション防止**: 
  - 既存のWebhook処理フローが変更されないことを確認するため、包括的なユニットテストを作成
  - 非同期処理の正しさを検証するためのタイムアウトと例外ハンドリングのテストを追加
- **検証コマンド追加**: `python -m pytest tests/unit/routers/ -k billing_webhook -v`

---

### Step 4: クレジット消費定数化 (`src/services/billing/credit_service.py`)
- **目的**:
  - `COST_PER_EPISODE = 1` （テキスト執筆）
  - `COST_PER_ILLUSTRATION = 5` （画像生成）
  定数化し、誤ったクレジット減算を防止。
- **検証コマンド**: `python -c "from src.services.billing.credit_service import CreditService; print(CreditService)"`
- **リグレッション防止**: 
  - 既存のクレジットサービスのAPIが変更されないことを確認するため、インターフェーステストを作成
  - 定数値が正しく使用されていることを�証するためのテストケースを追加
- **検証コマンド追加**: `python -m pytest tests/unit/services/billing/test_credit_service.py -v`

---

### Step 5: バックグラウンドタスクのクレジット管理健全化 (`src/backend/tasks/generation_tasks.py`)
- **目的**: セッションのクローズ漏れを防ぎ、執筆開始時にアトミックに減算を実行。
- **検証コマンド**: `pytest tests/unit/test_generation_tasks.py`
- **リグレッション防止**: 
  - 既存のバックグラウンドタスク機能が変更されないことを確認するため、包括的なテストスイートを実行
  - セッション管理とクレジット減算の原子性を検証するためのテストケースを追加
  - 例外発生時のクリーンアップ処理をテスト
- **検証コマンド追加**: `python -m pytest tests/unit/tasks/ -k generation -v`

---

### Step 6: クレジット減算テスト (`tests/unit/billing/test_credit_service_deduct.py`)
- **目的**: 残高0のユーザーが執筆を試みた際に `InsufficientCreditsError` が発生し、残高がマイナスにならないことをテスト。さらに、既存のクレジットサービス機能に対するリグレッションテストを追加。
- **実装内容**: 
  - 残高不足時のエラーハンドリングテスト
  - 二重消費防止テスト（競合状態での正常動作）
  - 通常のクレジット減算フローのテスト
  - エッジケーステスト（境界値、異常入力など）
- **検証コマンド**: `pytest tests/unit/billing/test_credit_service_deduct.py`
- **リグレッション防止強化**: 
  - テストカバレッジを90%以上維持することを確認
  - CIパイプラインで自動的にリグレッションテストを実行
  - テスト失敗時はブランチマージを防止する設定を追加

---

### Step 7: 共通クライアント確認 (`frontend/src/api/client.ts`)
- **目的**: `apiFetch` が `localStorage.getItem("auth_token")` を `Authorization: Bearer ...` にセットしていることを再確認。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - 既存のAPIクライアントの認証ヘッダー付与機能が変更されないことを確認するため、モックを使ったユニットテストを作成
  - トークンが存在しない場合や無効な場合の挙動をテスト
- **検証コマンド追加**: `cd frontend && npm test src/api/client.test.ts`

---

### Step 8: `api/graph.ts` 認証ヘッダー付与 (`frontend/src/api/graph.ts`)
- **目的**: 生の `fetch('/api/graph...')` を `apiFetch` に置換。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - GraphQL API呼び出しの機能が変更されないことを確認するため、モックを使ったユニットテストを作成
  - エラーハンドリングとタイムアウト処理のリグレッションテストを追加
- **検証コマンド追加**: `cd frontend && npm test src/api/graph.test.ts`

---

### Step 9: `api/editor.ts` 認証ヘッダー付与 (`frontend/src/api/editor.ts`)
- **目的**: 生の `fetch('/api/editor...')` を `apiFetch` に置換。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - エディタAPI呼び出しの機能が変更されないことを確認するため、モックを使ったユニットテストを作成
  - エラーハンドリングとタイムアウト処理のリグレッションテストを追加
- **検証コマンド追加**: `cd frontend && npm test src/api/editor.test.ts`

---

### Step 10: `PublishExportModal.tsx` 認証ヘッダー付与 (`frontend/src/components/common/PublishExportModal.tsx`)
- **目的**: 生の `fetch` を排除し、通信遮断を根絶。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/common/PublishExportModal.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 11: 低スペックコンテナ設定検証 (`scripts/verify_docker_config.py`)
- **目的**: 月額5,000円以内の安価なサーバー（CPU 1コア、RAM 1〜2GB）で安全に動作する docker-compose 設定を検証。
- **検証コマンド**: `python scripts/verify_docker_config.py`
- **リグレッション防止**: 
  - Docker設定の変更が既存のインフラ機能に影響しないことを確認するため、インテグレーションテストを作成
  - リソース使用量（CPU、メモリ、ディスク）が基準値を超えないことを検証するテストを追加
  - コンテナの起動時間と健康チェックのリグレッションテストを追加
- **検証コマンド追加**: 
  - `python scripts/verify_docker_config.py --verbose` (詳細な検証実行)
  - `python -m pytest tests/integration/test_docker_config.py -v` (Docker設定のインテグレーションテスト実行)

---

### Step 12: 課金・認証保護E2Eテスト (`tests/integration/test_billing_and_auth_guard.py`)
- **目的**: 未認証アクセスの401遮断、認証済みアクセスの許可、クレジット消費のライフサイクルを全結合検証。さらに、システム全体のリグレッション防止のためのベースラインテストとして機能させる。
- **実装内容**: 
  - 未認証アクセスの401エラーテスト
  - 認証済みアクセスの正常フローテスト
  - クレジット消費のライフサイクルテスト（付与→消費→残高確認）
  - エラーケースとエッジケースのテスト
  - パフォーマンスリグレッションテスト（応答時間が一定の閾値を超えないことを確認）
- **検証コマンド**: `pytest tests/integration/test_billing_and_auth_guard.py`
- **リグレッション防止強化**: 
  - E2EテストをCIパイプラインの必須チェック項目に追加
  - テスト結果のトレンドを監視し、パフォーマンスの劣化を早期検出
  - 本番環境と同等のデータ量でテストを実行し、スケーラビリティのリグレッションを防止
  - テストカバレッジレポートを生成し、重要なパスの見落としがないことを確認

---
### 🛡️ リグレッション防止戦略（全ステップ共通）

本実装計画では、以下のリグレッション防止策を全ステップにわたって実施します：

1. **段階的テスト追加**：各実装ステップにおいて、変更箇所に関するユニットテスト・統合テストを必ず追加または更新
2. **自動検証パイプライン**： 
   - プルリクエスト時に自動的にテストスイートを実行
   - テストカバレッジが基準値（80%）を下回る場合はマージをブロック
   - ビルド失敗時はデプロイを防止
3. **テスト種類の多様化**：
   - ユニットテスト：個別関数・クラスの動作検証
   - 統合テスト：モジュール間の連携検証
   - E2Eテスト：ユーザー視点での完全なワークフロー検証
   - ビジュアル回帰テスト：UIの意図しない変更検出（フロントエンド）
   - アクセシビリティテスト：a11y準拠のリグレッション防止
4. **継続的監視**：
   - テスト実行時間のトレンド監視（パフォーマンスリグレッション検出）
   - テスト失敗パターンの分析と予防的保守
   - 本番環境でのエラーレート監視とテストギャップの特定

この戦略により、課金・クレジット・インフラ健全化機能の追加による既存機能への影響を最小限に抑え、高品質なリリースを継続的に実現します。
