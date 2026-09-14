import stripe
from src.backend.config import settings
from typing import Optional

# Initialize Stripe with API key from settings
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

class StripeClient:
    """Stripe SDKラッパークラス"""
    
    @staticmethod
    def create_checkout_session(
        user_id: int,
        user_email: str,
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> str:
        """
        Stripe Checkout Sessionを生成してURLを返す
        
        Args:
            user_id: ユーザーID
            user_email: ユーザーのメールアドレス
            price_id: Stripe Price ID
            success_url: 成功時のリダイレクトURL
            cancel_url: キャンセル時のリダイレクトURL
            
        Returns:
            Checkout Session URL
        """
        try:
            # まずStripe Customerを取得または作成
            customer = StripeClient._get_or_create_customer(user_id, user_email)
            
            # Checkout Sessionを作成
            session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user_id)
                }
            )
            
            return session.url
        except Exception as e:
            # 本番環境では適切なロギングを行うべき
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    @staticmethod
    def create_customer_portal_session(stripe_customer_id: str, return_url: str) -> str:
        """
        Stripe Customer Portalセッションを生成してURLを返す
        
        Args:
            stripe_customer_id: Stripe Customer ID
            return_url: ポータルから戻るURL
            
        Returns:
            Customer Portal Session URL
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=return_url,
            )
            return session.url
        except Exception as e:
            raise Exception(f"Failed to create customer portal session: {str(e)}")
    
    @staticmethod
    def _get_or_create_customer(user_id: int, user_email: str):
        """
        ユーザーのStripe Customerを取得または作成
        実際の実装では、データベースからstripe_customer_idを取得し、
        存在しない場合のみ新規作成する
        """
        # ここでは簡略化のため、毎回新規作成するが、
        # 実際の実装ではデータベースと連携する
        try:
            # 既存の顧客をメールで検索（実際の実装ではデータベースからIDを取得）
            customers = stripe.Customer.list(email=user_email, limit=1)
            if customers.data:
                return customers.data[0]
            
            # 新規顧客作成
            customer = stripe.Customer.create(
                email=user_email,
                metadata={
                    'user_id': str(user_id)
                }
            )
            return customer
        except Exception as e:
            raise Exception(f"Failed to get or create customer: {str(e)}")