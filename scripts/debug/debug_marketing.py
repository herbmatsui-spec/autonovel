import asyncio
import sys
sys.path.insert(0, 'E:\\hhh')

from src.services.marketing import MarketingAgent

async def debug():
    agent = MarketingAgent(repo=None)
    try:
        zip_bytes, filename = await agent.create_export_package(book_id=1)
        print("Success")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())