# PLAN 11: Stripe連携とクレジット消費ロジック 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 課金・Stripe決済・クレジット消費・プラン制御基盤  
**目的**: LLM/マルチモーダル生成に伴うAPI原価を確実に回収し、フリーミアムから有料サブスク（Standard / Pro）への転換と従量クレジット購入を実現する。  
**前提**: 決済処理（Stripe）と残高管理（ローカルDBトランザクション）を明確に分離し、二重課金やクレジットの二重消費を防止する冪等設計。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/billing.py` (新規) | プラン定義、クレジット取引明細、決済セッション要求のPydanticモデル定義 |
| **2** | ORMモデル | `src/backend/database/models_billing.py` (新規) | `CreditTransaction`, `Subscription`, `StripeWebhookEvent` テーブル定義 |
| **3** | マイグレーション | `src/backend/alembic/versions/xxxx_billing_and_credits.py` (新規) | 課金台帳およびサブスクリプション管理テーブルのマイグレーション |
| **4** | 設定定義 | `src/config/billing_plans.py` (新規) | プラン別付与クレジット（月額）、およびタスク別消費クレジットレート表 |
| **5** | 取引ロジック | `src/services/billing/credit_service.py` (新規) | クレジット残高照会、残高仮押さえ（Hold）、確定（Commit）、返金（Refund） |
| **6** | ガード機構 | `src/backend/security/credit_guard.py` (新規) | 生成API実行前の残高検証と不足時402 Payment Required送出ミドルウェア |
| **7** | Stripe通信 | `src/services/billing/stripe_client.py` (新規) | Stripe Checkout Session生成、Customer Portalセッション発行、顧客管理 |
| **8** | Webhook受信 | `src/backend/routers/billing_webhook.py` (新規) | Stripe Webhook署名検証と決済完了・解約イベントの安全な非同期ハンドリング |
| **9** | APIルーター | `src/backend/routers/billing.py` (新規) | プラン一覧、Checkout開始、Portal遷移、取引明細照会エンドポイント |
| **10** | パイプライン統合 | `src/backend/tasks/generation_tasks.py` (修正) | 本文執筆・挿絵・音声合成完了時の実消費クレジット確定と失敗時自動返金 |
| **11** | フロントエンド | `frontend/src/components/billing/` (新規) | 残高バッジ、料金プランモーダル、クレジット不足警告チャージ誘導UI |
| **12** | 統合検証 | `tests/integration/test_billing_and_credits.py` (新規) | Stripeモックを用いた決済完了からクレジット反映、消費・枯渇ブロックのE2Eテスト |

---

## 各ステップの詳細仕様

### Step 1: 課金関連Pydanticモデル定義 (`src/models/billing.py`)
* **目標**: 課金・プラン・クレジット取引の入出力インターフェースを厳格に型定義。
* **実装内容**:
  ```python
  from __future__ import annotations
  from datetime import datetime
  from enum import Enum
  from pydantic import BaseModel, Field

  class PlanTier(str, Enum):
      FREE = "free"
      STARTER = "starter"      # JPY 980 / 月 (300クレジット)
      PRO = "pro"              # JPY 2,980 / 月 (1,200クレジット)
      ENTERPRISE = "enterprise"# JPY 9,800 / 月 (5,000クレジット)

  class TransactionType(str, Enum):
      MONTHLY_GRANT = "monthly_grant"  # サブスク月次付与
      PACK_PURCHASE = "pack_purchase"  # 都度クレジット購入
      CONSUMPTION = "consumption"      # 生成による消費
      REFUND = "refund"                # 失敗による返還
      ADMIN_ADJUST = "admin_adjust"    # 運営付与

  class CreateCheckoutRequest(BaseModel):
      price_id: str = Field(..., description="Stripe Price ID")
      mode: str = Field("subscription", pattern="^(subscription|payment)$")

  class CheckoutResponse(BaseModel):
      checkout_url: str

  class CreditBalanceResponse(BaseModel):
      balance: int
      plan_tier: PlanTier
      current_period_end: datetime | None = None
  ```
* **受け入れ基準**: `mypy src/models/billing.py` で型エラーゼロ。

---

### Step 2: 課金台帳ORMモデル定義 (`src/backend/database/models_billing.py`)
* **目標**: 監査可能なクレジット台帳とStripe状態を永続化。
* **実装内容**:
  ```python
  from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, text
  from src.infrastructure.database.models.base_orm import Base

  class CreditTransaction(Base):
      __tablename__ = "credit_transactions"

      id = Column(Integer, primary_key=True, autoincrement=True)
      user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
      amount: int = Column(Integer, nullable=False)  # 消費は負数、付与は正数
      balance_after: int = Column(Integer, nullable=False)
      transaction_type = Column(String(30), nullable=False)
      task_id = Column(String(100), nullable=True, index=True)
      description = Column(String(255), nullable=False)
      created_at = Column(DateTime, server_default=func.now())

  class Subscription(Base):
      __tablename__ = "subscriptions"

      id = Column(Integer, primary_key=True, autoincrement=True)
      user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
      stripe_subscription_id = Column(String(255), unique=True, nullable=False, index=True)
      stripe_customer_id = Column(String(255), nullable=False)
      plan_tier = Column(String(20), nullable=False)
      status = Column(String(30), nullable=False)  # active, canceled, past_due
      current_period_end = Column(DateTime, nullable=False)
  ```
* **受け入れ基準**: 外部キーおよびユニークインデックスが正しく宣言されていること。

---

### Step 3: Alembic マイグレーション作成 (`src/backend/alembic/versions/xxxx_billing_and_credits.py`)
* **目標**: 新規テーブル群をDBスキーマへ安全に追加。
* **実装内容**:
  - `credit_transactions`, `subscriptions`, `stripe_webhook_events` テーブルの生成。
  - `users.stripe_customer_id` へのインデックス作成。
* **受け入れ基準**: `alembic upgrade head` でロールバック（downgrade）も含め正常動作すること。

---

### Step 4: プランおよびタスク消費レート設定 (`src/config/billing_plans.py`)
* **目標**: クレジット消費ルールの一元管理。
* **実装内容**:
  ```python
  PLAN_CONFIG = {
      "free": {"price_jpy": 0, "monthly_credits": 50, "max_parallel_jobs": 1},
      "starter": {"price_jpy": 980, "monthly_credits": 300, "max_parallel_jobs": 2},
      "pro": {"price_jpy": 2980, "monthly_credits": 1200, "max_parallel_jobs": 4},
      "enterprise": {"price_jpy": 9800, "monthly_credits": 5000, "max_parallel_jobs": 10},
  }

  # 1クレジット ≒ 約 2.5〜3 円相当
  TASK_CREDIT_COSTS = {
      "plot_expansion": 2,       # プロット構成・ブレスト (Gemini Flash)
      "writing_standard": 10,    # 1エピソード本文執筆 (約3,000字 / Haiku or mini)
      "writing_climax_pro": 25,  # クライマックス最高品質執筆 (Claude 3.5 Sonnet)
      "audit_full": 5,           # 8オーディター並列監査
      "illustration_generate": 8,# 挿絵1枚生成 (SDXL / Imagen)
      "voice_synthesize": 6,     # VOICEVOX章音声合成
  }
  ```
* **受け入れ基準**: 設定辞書がイミュータブルであり、未定義タスク参照時の安全な例外処理が存在すること。

---

### Step 5: クレジット台帳サービス実装 (`src/services/billing/credit_service.py`)
* **目標**: DB行ロック（`SELECT FOR UPDATE`）を用いた厳密なクレジット取引。
* **実装内容**:
  - `deduct_credits(user_id, amount, task_id, description) -> bool`
  - `grant_credits(user_id, amount, type, description) -> int`
  - `get_balance(user_id) -> int`
  - トランザクション分離レベルに応じた二重引き落とし防止機構。
* **受け入れ基準**: 残高不足時に `InsufficientCreditsError` が発生し、ロールバックされること。

---

### Step 6: クレジット事前検証ガード (`src/backend/security/credit_guard.py`)
* **目標**: クレジット不足のユーザーが生成を開始できないように入口で弾く。
* **実装内容**:
  ```python
  def require_credits(task_type: str):
      async def dependency(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
          required = TASK_CREDIT_COSTS.get(task_type, 10)
          if current_user.credits < required:
              raise HTTPException(
                  status_code=status.HTTP_402_PAYMENT_REQUIRED,
                  detail={"error_code": "INSUFFICIENT_CREDITS", "required": required, "balance": current_user.credits}
              )
          return required
      return dependency
  ```
* **受け入れ基準**: クレジット不足時に HTTP 402 が即座に返され、LLMが呼び出されないこと。

---

### Step 7: Stripe SDKクライアント実装 (`src/services/billing/stripe_client.py`)
* **目標**: Stripe Checkout および Billing Portal へのセッション生成。
* **実装内容**:
  - `create_checkout_session(user_id: int, user_email: str, price_id: str, success_url: str, cancel_url: str) -> str`
  - `create_customer_portal_session(stripe_customer_id: str, return_url: str) -> str`
  - 顧客メタデータに `user_id` を確実に注入。
* **受け入れ基準**: 正しいリダイレクトURLが生成され、メタデータがStripe側に渡ること。

---

### Step 8: Stripe Webhook ハンドラー実装 (`src/backend/routers/billing_webhook.py`)
* **目標**: 決済完了やサブスク更新を非同期に受領し、クレジットを付与。
* **実装内容**:
  - `POST /api/billing/webhook`: `stripe.Webhook.construct_event` による署名検証。
  - `checkout.session.completed`: 初期クレジットの即時付与。
  - `invoice.payment_succeeded`: サブスク月次更新クレジットの自動付与。
  - `customer.subscription.deleted`: フリープランへのダウングレード。
  - イベントIDの重複処理防止（Idempotency Cache）。
* **受け入れ基準**: 同一イベントを2回受信してもクレジットが二重付与されないこと。

---

### Step 9: 課金APIルーター (`src/backend/routers/billing.py`)
* **目標**: フロントエンドから呼び出す課金関連API。
* **実装内容**:
  - `GET /api/billing/plans`: 利用可能なプランと価格一覧の取得。
  - `GET /api/billing/balance`: 現在のユーザー残高と今月の消費統計。
  - `POST /api/billing/create-checkout-session`: 決済画面URL取得。
  - `POST /api/billing/create-portal-session`: クレジットカード変更・解約ポータルURL取得。
* **受け入れ基準**: 認証されたユーザーが自分の決済ポータルURLを正常取得できること。

---

### Step 10: 生成パイプラインへのクレジット消費統合 (`src/backend/tasks/generation_tasks.py`)
* **目標**: 生成の成功時に実消費を記録し、例外発生時にはクレジットを保護。
* **実装内容**:
  - 執筆タスク開始時にクレジットを仮確保。
  - LLM呼び出し成功時に `credit_service.deduct_credits(...)` をコミット。
  - サーバーダウンやLLMの500エラー発生時は引き落としを行わずロールバック。
* **受け入れ基準**: 途中で生成エラーが発生した場合にユーザーのクレジットが減らないこと。

---

### Step 11: フロントエンド課金UIコンポーネント (`frontend/src/components/billing/`)
* **目標**: 残高表示、プラン比較、ワンクリック課金導線の提供。
* **実装内容**:
  - `CreditBalanceBadge.tsx`: ヘッダー右上に現在の残クレジット（例: 🪙 420 pt）を表示。
  - `PricingModal.tsx`: Free / Starter / Pro のプラン比較カードと「プランをアップグレード」ボタン。
  - `LowCreditModal.tsx`: クレジット不足時に自動ポップアップするチャージ案内。
* **受け入れ基準**: 残高がリアルタイムにヘッダーへ反映され、モーダルからStripeへ遷移できること。

---

### Step 12: 課金＆クレジット統合テスト (`tests/integration/test_billing_and_credits.py`)
* **目標**: 決済〜付与〜消費〜枯渇ブロックの一連の流れを自動検証。
* **実装内容**:
  - Webhookモックを発行してクレジットが50 -> 350に増加することを確認。
  - 本文執筆APIを呼び出し、10クレジット減算されることを確認。
  - クレジットを0にした状態で生成APIを叩き、402エラーで拒絶されることを確認。
* **受け入れ基準**: `pytest tests/integration/test_billing_and_credits.py` が PASS すること。
