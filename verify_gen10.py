import os
import time
import requests
from pathlib import Path

# Load .env
env_path = Path(r"I:\R15\cR15\.env")
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Get API key
api_key = os.environ.get("GEMINI_API_KEY")

# Define the request parameters
api_url = "http://localhost:8200/api/easy_mode/generate"
headers = {"Content-Type": "application/json"}

# Configuration for 10 episodes
config = {
    "genre": "異世界転生",
    "keywords": "最強,ざまぁ,カタルシス,無双",
    "archetype_key": "王道ざまぁ（爽快感最大）",
    "target_eps": 10,
    "initial_limit": 3,
    "word_count": 3000,
    "concept": "検証用: 3000字×10話の自動生成テスト",
    "tone_vibe": 0.7
}

# Prepare the request
request_data = {
    "api_key": api_key,
    "config": config,
    "trace_id": "verify10"
}

# Make the API call
print("Starting generation...")
t0 = time.time()

try:
    response = requests.post(api_url, json=request_data, headers=headers, timeout=300)
    response.raise_for_status()
    result = response.json()
    print("Generation successful!")
    print(f"Task ID: {result['task_id']}")
    print(f"Estimated cost: ${result.get('estimated_cost', 0):.4f}")
    print(f"Total time: {time.time() - t0:.2f} seconds")
    
    # Check if generation is complete
    if "task_id" in result:
        print("Generation in progress. Task ID:", result['task_id'])
    else:
        print("Generation completed or failed:", result)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()