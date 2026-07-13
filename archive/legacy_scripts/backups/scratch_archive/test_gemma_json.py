import os

from google import genai
from google.genai import types as genai_types


def main():
    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4")
    client = genai.Client(api_key=api_key)

    print("Testing gemma-4-31b-it WITHOUT JSON mode:")
    try:
        response = client.models.generate_content(
            model="gemma-4-31b-it",
            contents="Hello, please write a short 1-sentence greeting."
        )
        print(f"Success! Response: {response.text}")
    except Exception as e:
        print(f"Failed WITHOUT JSON: {e}")

    print("\nTesting gemma-4-31b-it WITH JSON mode:")
    try:
        config = genai_types.GenerateContentConfig(
            response_mime_type="application/json"
        )
        response = client.models.generate_content(
            model="gemma-4-31b-it",
            contents="Output a JSON with a single key 'greeting' containing a greeting.",
            config=config
        )
        print(f"Success! Response: {response.text}")
    except Exception as e:
        print(f"Failed WITH JSON: {e}")

if __name__ == "__main__":
    main()

