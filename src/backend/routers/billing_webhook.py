import stripe
import json
from fastapi import APIRouter, Request, Header, HTTPException, Depends
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database import get_db
from src.services.billing.credit_service import CreditService
from src.backend.database.models import User
from src.backend.database.models_billing import Subscription
from src.backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing/webhook", tags=["billing-webhook"])

# Webhook署名の検証用エンドポイントシークレット
WEBHOOK_SECRET = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

@router.post("")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Stripe Webhookを受信して処理する
    
    セキュリティのため、Webhook署名の検証を行う
    """
    # リクエストボディを取得
    payload = await request.body()
    
    try:
        # Webhook署名を検証
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, WEBHOOK_SECRET
        )
    except ValueError as e:
        # 不正なペイロード
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        # 不正な署名
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")
    
    # イベントタイプ別に処理を分岐
    event_type = event['type']
    event_data = event['data']['object']
    
    # イベントの重複処理を防止するため、イベントIDを記録すべき
    # ここでは簡略化のため、主要なイベントタイプのみ処理
    
    if event_type == 'checkout.session.completed':
        await _handle_checkout_session_completed(event_data, db)
    elif event_type == 'invoice.payment_succeeded':
        await _handle_invoice_payment_succeeded(event_data, db)
    elif event_type == 'customer.subscription.deleted':
        await _handle_customer_subscription_deleted(event_data, db)
    elif event_type == 'customer.subscription.updated':
        await _handle_customer_subscription_updated(event_data, db)
    # その他のイベントタイプについては必要に応じて追加
    
    return {"status": "success"}

async def _handle_checkout_session_completed(session, db: AsyncSession):
    """Checkout Session完了時に初回クレジットを付与"""
    try:
        # ユーザーIDをメタデータから取得
        user_id = int(session.get('metadata', {}).get('user_id', 0))
        if user_id == 0:
            # メタデータにユーザーIDがない場合は、Customer IDから検索
            stripe_customer_id = session.get('customer')
            if stripe_customer_id:
                result = await db.execute(
                    select(User).where(User.stripe_customer_id == stripe_customer_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    user_id = user.id
        
        if user_id == 0:
            # ユーザーIDが取得できない場合はログに記録して終了
            # 実際の実装では適切なロギングを行う
            return
        
        # サブスクリプションIDを取得
        subscription_id = session.get('subscription')
        if not subscription_id:
            return
        
        # サブスクリプション詳細を取得
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # ユーザー情報を取得
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        
        # クレジットサービスを初期化
        credit_service = CreditService(db)
        
        # プランに応じた初回クレジットを付与
        # 実際の価格IDとプランのマッピングが必要だが、
        # ここではサブスクリプションからプラン情報を取得する想定
        credits_to_grant = 0
        if subscription.items.data:
            price_id = subscription.items.data[0].price.id
            # プラン別のクレジット付与額を設定（実際の設定から取得すべき）
            # 一時的にハードコーディング（後で設定ファイルから取得するように修正すべき）
            plan_credits = {
                'price_free': 0,      # フリープラン
                'price_starter': 300, # スタータープラン
                'price_pro': 1200,    # プロプラン
                'price_enterprise': 5000 # エンタープライズプラン
            }
            credits_to_grant = plan_credits.get(price_id, 0)
        
        if credits_to_grant > 0:
            # クレジットを付与
            await credit_service.grant_credits(
                user_id=user_id,
                amount=credits_to_grant,
                transaction_type="monthly_grant",
                description=f"Initial credit grant for {subscription.plan.nickname or 'subscription'}",
                task_id=None
            )
            
            # サブスクリプションレコードを作成または更新
            await _create_or_update_subscription_record(user, subscription, db)
            
    except Exception as e:
        logger.error(f"Error handling checkout session completed: {e}", exc_info=True)
        pass

async def _handle_invoice_payment_succeeded(invoice, db: AsyncSession):
    """インボイス支払い成功時に月次クレジットを付与"""
    try:
        # サブスクリプションIDを取得
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        
        # サブスクリプション詳細を取得
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Customer IDを取得
        stripe_customer_id = subscription.customer
        if isinstance(stripe_customer_id, dict):
            stripe_customer_id = stripe_customer_id.get('id')
        
        # ユーザーを検索
        result = await db.execute(
            select(User).where(User.stripe_customer_id == stripe_customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        
        # クレジットサービスを初期化
        credit_service = CreditService(db)
        
        # 月次クレジットを付与
        credits_to_grant = 0
        if subscription.items.data:
            price_id = subscription.items.data[0].price.id
            # プラン別のクレジット付与額を設定
            plan_credits = {
                'price_free': 0,
                'price_starter': 300,
                'price_pro': 1200,
                'price_enterprise': 5000
            }
            credits_to_grant = plan_credits.get(price_id, 0)
        
        if credits_to_grant > 0:
            await credit_service.grant_credits(
                user_id=user.id,
                amount=credits_to_grant,
                transaction_type="monthly_grant",
                description=f"Monthly credit grant for {subscription.plan.nickname or 'subscription'}",
                task_id=None
            )
            
            # サブスクリプションレコードを更新
            await _create_or_update_subscription_record(user, subscription, db)
            
    except Exception as e:
        # エラーが発生してもWebhookは200を返すべき
        pass

async def _handle_customer_subscription_deleted(subscription, db: AsyncSession):
    """サブスクリプション削除時にフリープランにダウングレード"""
    try:
        # Customer IDを取得
        stripe_customer_id = subscription.customer
        if isinstance(stripe_customer_id, dict):
            stripe_customer_id = stripe_customer_id.get('id')
        
        # ユーザーを検索
        result = await db.execute(
            select(User).where(User.stripe_customer_id == stripe_customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        
        # ユーザーをフリープランにダウングレード
        user.plan_tier = "free"
        # 注意: 実際の実装ではデータベースのコミットが必要
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        pass

async def _handle_customer_subscription_updated(subscription, db: AsyncSession):
    """サブスクリプション更新時に情報を同期"""
    try:
        # Customer IDを取得
        stripe_customer_id = subscription.customer
        if isinstance(stripe_customer_id, dict):
            stripe_customer_id = stripe_customer_id.get('id')
        
        # ユーザーを検索
        result = await db.execute(
            select(User).where(User.stripe_customer_id == stripe_customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        
        # サブスクリプションレコードを更新
        await _create_or_update_subscription_record(user, subscription, db)
        
    except Exception as e:
        await db.rollback()
        pass

async def _create_or_update_subscription_record(user: User, subscription, db: AsyncSession):
    """サブスクリプションレコードを作成または更新"""
    from src.backend.database.models_billing import Subscription as SubscriptionModel
    
    # 既存のサブスクリプションレコードを検索
    result = await db.execute(
        select(SubscriptionModel).where(SubscriptionModel.user_id == user.id)
    )
    db_subscription = result.scalar_one_or_none()
    
    if db_subscription:
        # 既存レコードを更新
        db_subscription.stripe_subscription_id = subscription.id
        db_subscription.stripe_customer_id = subscription.customer
        db_subscription.plan_tier = subscription.items.data[0].price.id if subscription.items.data else "unknown"
        db_subscription.status = subscription.status
        db_subscription.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
    else:
        # 新規レコードを作成
        new_subscription = SubscriptionModel(
            user_id=user.id,
            stripe_subscription_id=subscription.id,
            stripe_customer_id=subscription.customer,
            plan_tier=subscription.items.data[0].price.id if subscription.items.data else "unknown",
            status=subscription.status,
            current_period_end=datetime.fromtimestamp(subscription.current_period_end)
        )
        db.add(new_subscription)
    
    await db.commit()