import asyncio
import sys
from pathlib import Path

# Add current workspace directory to sys.path to resolve imports
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from unittest.mock import MagicMock

from agents.llm_provider import GeminiClient

from backend.engine_utils import AdaptiveCooldown


async def test_cache():
    # Mock dependencies
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"status": "success"}'
    mock_response.usage_metadata = None
    mock_client.models.generate_content.return_value = mock_response

    cooldown = AdaptiveCooldown(base_sec=0, min_sec=0, max_sec=0)

    client = GeminiClient(mock_client, cooldown)

    print("Testing generate_json caching...")

    # 1st call (cache miss)
    metadata, story, usage = await client.generate_json(
        model_name="gemini-1.5-flash",
        prompt="Test prompt",
        temp=0.7,
        use_cache=True,
        max_retries=1
    )
    print(f"   [1st Call] metadata: {metadata}")
    assert mock_client.models.generate_content.call_count == 1, "First call should invoke the API"

    # 2nd call (cache hit)
    metadata2, story2, usage2 = await client.generate_json(
        model_name="gemini-1.5-flash",
        prompt="Test prompt",
        temp=0.7,
        use_cache=True,
        max_retries=1
    )
    print(f"   [2nd Call] metadata: {metadata2}")
    assert mock_client.models.generate_content.call_count == 1, "Second call should hit the cache and NOT invoke the API"

    # 3rd call with use_cache=False (should bypass cache)
    metadata3, story3, usage3 = await client.generate_json(
        model_name="gemini-1.5-flash",
        prompt="Test prompt",
        temp=0.7,
        use_cache=False,
        max_retries=1
    )
    print(f"   [3rd Call (Bypass)] metadata: {metadata3}")
    assert mock_client.models.generate_content.call_count == 2, "Third call with use_cache=False should bypass cache and invoke the API"

    print("SUCCESS: GeminiClient.generate_json cache works perfectly!")

    print("\nTesting generate_text caching...")
    # Reset mock
    mock_client.models.generate_content.reset_mock()

    # 1st text call (cache miss)
    text1 = await client.generate_text(
        model_name="gemini-1.5-flash",
        prompt="Test prompt text",
        temp=0.7,
        use_cache=True
    )
    print(f"   [1st Call] text: {text1}")
    assert mock_client.models.generate_content.call_count == 1, "First call should invoke the API"

    # 2nd text call (cache hit)
    text2 = await client.generate_text(
        model_name="gemini-1.5-flash",
        prompt="Test prompt text",
        temp=0.7,
        use_cache=True
    )
    print(f"   [2nd Call] text: {text2}")
    assert mock_client.models.generate_content.call_count == 1, "Second call should hit the cache and NOT invoke the API"

    print("SUCCESS: GeminiClient.generate_text cache works perfectly!")

if __name__ == "__main__":
    asyncio.run(test_cache())

