import asyncio
import os

from google import genai


async def run_audit():
    # 1. APIキーの設定
    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4")
    client = genai.Client(api_key=api_key)

    # 2. テスト用データの定義（test_integration.py で発生するプロンプトを模倣）
    synopsis = "追放された雑用係が実は最強の付与術師で、自分を追い出した勇者パーティーが破滅していくのを横目に、エルフの美少女とスローライフを満喫する"
    world_settings_json = "{}"

    from models import HegemonyAuditResult
    schema_json = HegemonyAuditResult.model_json_schema()

    # engine_prompts の build_plot_integrity_audit_prompt をエミュレート
    prompt = (
        f"あなたは覇権小説プロデューサーであり、論理監査エージェントです。\n"
        f"以下の「企画あらすじ」および「世界観設定」の整合性を検証し、設定間の自己矛盾や因果律の崩壊がないかを監査してください。\n\n"
        f"【企画あらすじ】\n{synopsis}\n\n"
        f"【世界観設定】\n{world_settings_json}\n\n"
        f"以下のスキーマに従ってJSONオブジェクトとして回答を出力してください。\n"
        f"{schema_json}\n"
    )

    print("Sending request to gemini-3.1-flash-lite...")
    try:
        from google.genai import types as genai_types

        from backend.engine_utils import flatten_pydantic_schema

        # モデルルーティングに合わせる（MODEL_PLANNING = gemini-3.1-flash-lite）
        model = "gemini-3.1-flash-lite"

        config = genai_types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=flatten_pydantic_schema(schema_json)
        )

        def _call():
            return client.models.generate_content(
                model=model, contents=[prompt], config=config
            )

        res = await asyncio.to_thread(_call)
        print("Success!")
        print(f"Response: {res.text}")
    except Exception:
        import traceback
        traceback.print_exc()

asyncio.run(run_audit())

