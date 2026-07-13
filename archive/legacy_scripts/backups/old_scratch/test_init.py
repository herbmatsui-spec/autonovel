import asyncio
import os

from backend.engine import UltimateHegemonyEngine


async def test_init():
    print("Initializing engine...")
    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4")
    engine = UltimateHegemonyEngine(api_key=api_key)
    print("Engine initialized successfully.")
    print(f"Repo: {engine.repo}")
    print(f"Config: {engine.config.get('max_concurrency')}")

if __name__ == "__main__":
    asyncio.run(test_init())

