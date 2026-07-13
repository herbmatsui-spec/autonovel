import os

from google import genai

api_key = os.environ.get("GEMINI_API_KEY", "")
print(f"API Key present: {bool(api_key)}")

if api_key:
    client = genai.Client(api_key=api_key)
    try:
        print("Listing models...")
        for m in client.models.list():
            if "flash" in m.name or "pro" in m.name or "gemma" in m.name:
                print(f" - {m.name} ({m.supported_actions})")
    except Exception as e:
        print(f"Error listing models: {e}")
else:
    print("No GEMINI_API_KEY env var set.")

