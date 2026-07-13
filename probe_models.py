import os, sys, time
from pathlib import Path
env_path = Path(r"I:\R15\cR15\.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
sys.path.insert(0, r"I:\R15\cR15")
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash-lite",
          "gemini-flash-lite", "gemini-2.5-flash"]
for m in models:
    try:
        resp = client.models.generate_content(model=m, contents="こんにちは、1文字で返答してください。",
                                              config={"temperature": 0.5, "max_output_tokens": 16})
        u = getattr(resp, "usage_metadata", None)
        pt = getattr(u, "prompt_token_count", 0) if u else 0
        ct = getattr(u, "candidates_token_count", 0) if u else 0
        print(f"OK   {m}: text={repr(resp.text)[:30]} pt={pt} ct={ct}", flush=True)
    except Exception as e:
        print(f"FAIL {m}: {str(e)[:160]}", flush=True)
    time.sleep(2)
print(">>> PROBE DONE", flush=True)
