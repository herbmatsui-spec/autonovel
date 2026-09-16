import asyncio
import sys
sys.path.insert(0, 'E:\\hhh')

from tests.unit.services.test_marketing import (
    test_create_export_package_fallback,
    test_create_export_package_with_repo_returns_none,
    test_create_export_package_with_repo_data,
    test_create_export_package_with_book_data_override,
)

async def run_tests():
    await test_create_export_package_fallback()
    print("test_fallback passed")
    await test_create_export_package_with_repo_returns_none()
    print("test_repo_none passed")
    await test_create_export_package_with_repo_data()
    print("test_repo_data passed")
    await test_create_export_package_with_book_data_override()
    print("test_book_data_override passed")
    print("All tests passed")

if __name__ == "__main__":
    asyncio.run(run_tests())