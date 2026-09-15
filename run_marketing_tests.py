import importlib.util
import sys
# Load the services marketing module directly from file to avoid package shadowing
spec = importlib.util.spec_from_file_location("marketing", "E:\\hhh\\src\\services\\marketing.py")
marketing = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = marketing
spec.loader.exec_module(marketing)
MarketingAgent = marketing.MarketingAgent

import asyncio
from tests.unit.services.test_marketing import (
    test_create_export_package_fallback,
    test_create_export_package_with_repo_returns_none,
    test_create_export_package_with_repo_data,
    test_create_export_package_with_book_data_override,
)

async def run_all():
    await test_create_export_package_fallback()
    print("test_create_export_package_fallback passed")
    await test_create_export_package_with_repo_returns_none()
    print("test_create_export_package_with_repo_returns_none passed")
    await test_create_export_package_with_repo_data()
    print("test_create_export_package_with_repo_data passed")
    await test_create_export_package_with_book_data_override()
    print("test_create_export_package_with_book_data_override passed")
    print("All tests passed!")

if __name__ == "__main__":
    asyncio.run(run_all())