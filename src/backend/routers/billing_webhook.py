import asyncio
import logging
from datetime import datetime
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.backend.database import get_db
from src.backend.database.models import User
from src.backend.database.models_billing import StripeWebhookEvent, Subscription
from src.config.billing_plans import get_credits_for_price_id, get_tier_for_price_id
from src.services.billing.credit_service import CreditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing/webhook", tags=["billing-webhook"])

# Webhook署名の検証用エンドポイントシークレット
WEBHOOK_SECRET = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")


@router.post("")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """Stripe Webhookを受信して安全・非同期かつべき等に処理する。"""
    payload = await request.body()

    try:
        if WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, WEBHOOK_SECRET
            )
        else:
            # 開発・テスト環境でシークレット未設定時
            import json
            event = json.loads(payload)
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    event_id = event.get("id")
    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})

    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event ID")

    # べき等性チェック: 既に処理済みのイベントなら即座に 200 OK を返却
    existing_event = await db.get(StripeWebhookEvent, event_id)
    if existing_event:
        if existing_event.status == "processed":
            logger.info(f"Stripe event {event_id} already processed. Skipping duplicate.")
            return {"status": "already_processed", "event_id": event_id}
        elif existing_event.status == "processing":
            # 処理中イベントのタイムアウト判定 (10分以上経過していれば前回の処理クラッシュとみなして再試行)
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            created = existing_event.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created and (now - created) > timedelta(minutes=10):
                logger.warning(
                    f"Stripe event {event_id} was stuck in processing since {created}. Retrying processing."
                )
                existing_event.status = "processing"
                webhook_record = existing_event
            else:
                logger.info(f"Stripe event {event_id} is currently being processed. Skipping concurrent duplicate.")
                return {"status": "already_processing", "event_id": event_id}
        else:
            # status == "failed": 前回失敗したイベントの再試行
            logger.warning(f"Stripe event {event_id} previously failed. Retrying processing.")
            existing_event.status = "processing"
            webhook_record = existing_event
    else:
        # イベントを processing 状態で記録
        webhook_record = StripeWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            status="processing",
        )
        db.add(webhook_record)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        # 同時並行リクエストで既にコミットされた場合
        return {"status": "already_processed", "event_id": event_id}

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_session_completed(event_data, db, event_id=event_id)
        elif event_type == "invoice.payment_succeeded":
            await _handle_invoice_payment_succeeded(event_data, db, event_id=event_id)
        elif event_type == "customer.subscription.deleted":
            await _handle_customer_subscription_deleted(event_data, db)
        elif event_type == "customer.subscription.updated":
            await _handle_customer_subscription_updated(event_data, db)
        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")

        webhook_record.status = "processed"
        await db.commit()
    except Exception as e:
        logger.error(f"Error handling Stripe webhook event {event_id}: {e}", exc_info=True)
        webhook_record.status = "failed"
        await db.commit()
        # Stripeのリトライを防ぐため、内部エラー時もログを残した上で200を返すか、再試行させたい場合はエラー送出
        return {"status": "error", "event_id": event_id, "detail": str(e)}

    return {"status": "success", "event_id": event_id}


async def _handle_checkout_session_completed(
    session: dict, db: AsyncSession, event_id: Optional[str] = None
):
    """Checkout Session完了時に初回クレジットを付与"""
    user_id = int(session.get("metadata", {}).get("user_id", 0))
    if user_id == 0:
        stripe_customer_id = session.get("customer")
        if stripe_customer_id:
            result = await db.execute(
                select(User).where(User.stripe_customer_id == stripe_customer_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user_id = user.id

    if user_id == 0:
        logger.warning(f"Could not determine user_id for checkout session: {session.get('id')}")
        return

    subscription_id = session.get("subscription")
    if not subscription_id:
        return

    # 同期ネットワーク呼び出しを非同期スレッドにオフロード
    subscription = await asyncio.to_thread(stripe.Subscription.retrieve, subscription_id)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return

    credit_service = CreditService(db)

    credits_to_grant = 0
    if subscription.items.data:
        price_id = subscription.items.data[0].price.id
        credits_to_grant = get_credits_for_price_id(price_id)
        user.plan_tier = get_tier_for_price_id(price_id)

    if credits_to_grant > 0:
        await credit_service.grant_credits(
            user_id=user_id,
            amount=credits_to_grant,
            transaction_type="monthly_grant",
            description=f"Initial credit grant for {getattr(subscription.plan, 'nickname', None) or 'subscription'}",
            task_id=f"stripe_evt_{event_id}" if event_id else None,
            auto_commit=False,
        )

    await _create_or_update_subscription_record(user, subscription, db)


async def _handle_invoice_payment_succeeded(
    invoice: dict, db: AsyncSession, event_id: Optional[str] = None
):
    """インボイス支払い成功時に月次クレジットを付与"""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    subscription = await asyncio.to_thread(stripe.Subscription.retrieve, subscription_id)

    stripe_customer_id = subscription.customer
    if isinstance(stripe_customer_id, dict):
        stripe_customer_id = stripe_customer_id.get("id")

    result = await db.execute(
        select(User).where(User.stripe_customer_id == stripe_customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"User with stripe_customer_id {stripe_customer_id} not found")
        return

    credit_service = CreditService(db)

    credits_to_grant = 0
    if subscription.items.data:
        price_id = subscription.items.data[0].price.id
        credits_to_grant = get_credits_for_price_id(price_id)
        user.plan_tier = get_tier_for_price_id(price_id)

    if credits_to_grant > 0:
        await credit_service.grant_credits(
            user_id=user.id,
            amount=credits_to_grant,
            transaction_type="monthly_grant",
            description=f"Monthly credit grant for {getattr(subscription.plan, 'nickname', None) or 'subscription'}",
            task_id=f"stripe_evt_{event_id}" if event_id else None,
            auto_commit=False,
        )

    await _create_or_update_subscription_record(user, subscription, db)


async def _handle_customer_subscription_deleted(subscription, db: AsyncSession):
    """サブスクリプション削除時にフリープランにダウングレード"""
    stripe_customer_id = subscription.customer
    if isinstance(stripe_customer_id, dict):
        stripe_customer_id = stripe_customer_id.get("id")

    result = await db.execute(
        select(User).where(User.stripe_customer_id == stripe_customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.plan_tier = "free"
    await db.flush()


async def _handle_customer_subscription_updated(subscription, db: AsyncSession):
    """サブスクリプション更新時に情報を同期"""
    stripe_customer_id = subscription.customer
    if isinstance(stripe_customer_id, dict):
        stripe_customer_id = stripe_customer_id.get("id")

    result = await db.execute(
        select(User).where(User.stripe_customer_id == stripe_customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    await _create_or_update_subscription_record(user, subscription, db)


async def _create_or_update_subscription_record(user: User, subscription, db: AsyncSession):
    """サブスクリプションレコードを作成または更新"""
    from src.backend.database.models_billing import Subscription as SubscriptionModel

    result = await db.execute(
        select(SubscriptionModel).where(SubscriptionModel.user_id == user.id)
    )
    db_subscription = result.scalar_one_or_none()

    price_id = subscription.items.data[0].price.id if subscription.items.data else "unknown"
    period_end = datetime.fromtimestamp(subscription.current_period_end)

    if db_subscription:
        db_subscription.stripe_subscription_id = subscription.id
        db_subscription.stripe_customer_id = subscription.customer
        db_subscription.plan_tier = price_id
        db_subscription.status = subscription.status
        db_subscription.current_period_end = period_end
    else:
        new_subscription = SubscriptionModel(
            user_id=user.id,
            stripe_subscription_id=subscription.id,
            stripe_customer_id=subscription.customer,
            plan_tier=price_id,
            status=subscription.status,
            current_period_end=period_end,
        )
        db.add(new_subscription)

    await db.flush()