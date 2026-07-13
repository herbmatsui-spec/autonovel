import asyncio

from google import genai


async def test():
    key = "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4"
    print(f"Initializing client with key: {key}")
    client = genai.Client(api_key=key)

    def _call():
        print("Calling generate_content with gemini-3.1-flash-lite...")
        return client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=["Hello! Say 'Key is working!'"],
        )
    try:
        response = await asyncio.to_thread(_call)
        print(f"Success! Response text: {response.text}")
    except Exception as e:
        print(f"Failed! Error: {e}")

asyncio.run(test())

