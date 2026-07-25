import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from src.models.easy_mode_schemas import (
    DigestRequest,
    GachaRequest,
    PromotionRequest,
)
from src.services.digest_service import DigestService
from src.services.gacha_service import GachaService
from src.services.promotion_service import PromotionService


async def main():
    print("--- 1. Testing GachaService ---")
    gacha_service = GachaService()
    req = GachaRequest(genre="ファンタジー", keywords=["無双", "魔法"], temperature=0.7)
    res = await gacha_service.generate_plans(req)
    print(f"Request ID: {res.request_id}")
    print(f"Plans count: {len(res.plans)}")

    assert len(res.plans) == 3
    selected_plan_id = res.plans[0].plan_id

    print("\n--- 2. Testing DigestService ---")
    digest_service = DigestService()
    digest_req = DigestRequest(request_id=res.request_id, selected_plan_id=selected_plan_id)
    digest_res = await digest_service.generate_digest(digest_req)
    print(f"Book ID: {digest_res.book_id}")
    print(f"Status: {digest_res.status}")
    assert digest_res.book_id is not None

    print("\n--- 3. Testing PromotionService ---")
    promo_service = PromotionService()
    promo_req = PromotionRequest(book_id=digest_res.book_id)
    promo_res = promo_service.promote(promo_req)
    print(f"Success: {promo_res.success}")
    print(f"Redirect URL: {promo_res.redirect_url}")
    print(f"Token: {promo_res.state_token}")
    assert promo_res.success is True

    print("\n[SUCCESS] All standalone unit tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
