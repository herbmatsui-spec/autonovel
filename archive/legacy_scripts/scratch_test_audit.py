import asyncio

from agents.llm_provider import GeminiClient
from google import genai

from backend.engine_utils import AdaptiveCooldown
from models.audit import HegemonyAuditResult
from models.base import LLMRequestOptions


async def test():
    key = "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4"
    client = genai.Client(api_key=key)
    cooldown = AdaptiveCooldown(0.0, 0.0, 90.0)
    base_llm = GeminiClient(client, cooldown)

    synopsis = "追放された雑用係が実は最強の付与術師で、自分を追い出した勇者パーティーが破滅していくのを横目に、エルフの美少女とスローライフを満喫する"
    world_rules_json = '{"rules": ["魔法には代償がある", "勇者パーティーは傲慢である"]}'
    schema_json = HegemonyAuditResult.model_json_schema()

    prompt = (
        "あなたは物語の整合性監査官です。以下のあらすじと世界設定に矛盾がないか確認してください。\n\n"
        f"【あらすじ】\n{synopsis}\n\n"
        f"【世界設定】\n{world_rules_json}\n\n"
        "Output strictly conforming to the response schema."
    )

    request = LLMRequestOptions(
        model_name="gemini-3.1-flash-lite",
        prompt=prompt,
        response_schema=HegemonyAuditResult,
        temp=0.1,
        use_cache=False
    )

    print("Sending generate_json request to gemini-3.1-flash-lite...")
    try:
        metadata, story, usage = await base_llm.generate_json(request)
        print("Success!")
        print("Metadata:", metadata)
    except Exception as e:
        print("Failed with error:", e)

asyncio.run(test())

