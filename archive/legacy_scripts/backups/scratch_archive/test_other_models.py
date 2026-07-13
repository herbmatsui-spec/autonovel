import os

from google import genai
from google.genai import types as genai_types


def test_model(client, model_name):
    print(f"Testing {model_name}:")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Hello, please write a short 1-sentence greeting."
        )
        print(f"  Text success! Response: {response.text}")
    except Exception as e:
        print(f"  Text failed: {e}")

    try:
        config = genai_types.GenerateContentConfig(
            response_mime_type="application/json"
        )
        response = client.models.generate_content(
            model=model_name,
            contents="Output a JSON with a single key 'greeting' containing 'hello'.",
            config=config
        )
        print(f"  JSON success! Response: {response.text}")
    except Exception as e:
        print(f"  JSON failed: {e}")

def main():
    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4")
    client = genai.Client(api_key=api_key)

    models_to_test = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite"
    ]

    for m in models_to_test:
        test_model(client, m)
        print()

if __name__ == "__main__":
    main()

