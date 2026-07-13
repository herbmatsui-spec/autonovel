import os

from google import genai


def main():
    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyD5vwqaRbquOO554oX7pfESV7Rv5ooleR4")
    print(f"Using API Key prefix: {api_key[:10]}...")

    try:
        client = genai.Client(api_key=api_key)
        print("Successfully created genai.Client")

        print("\nListing available models:")
        models = client.models.list()
        for m in models:
            print(f"- {m.name} (supported_actions: {m.supported_actions})")

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()

