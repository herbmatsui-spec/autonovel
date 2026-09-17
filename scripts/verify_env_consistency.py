"""config.py と .env.example のキー整合性を検証するスクリプト。"""
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.backend.config import Settings

def check_consistency():
    config_keys = set(Settings.model_fields.keys())

    env_example_path = Path(".env.example")
    if not env_example_path.exists():
        raise FileNotFoundError(".env.example does not exist")

    example_keys = set()
    for line in env_example_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            example_keys.add(key)

    missing_in_example = config_keys - example_keys
    # システム内部生成値などは除外許容
    ignored = {"STORAGE_DIR", "ROOT_DIR", "model_config"}
    missing_in_example -= ignored

    print(f"Config keys: {len(config_keys)}, Example keys: {len(example_keys)}")
    if missing_in_example:
        print(f"WARNING: Keys in config.py but missing in .env.example: {missing_in_example}")
    else:
        print("SUCCESS: config.py and .env.example are in sync!")

if __name__ == "__main__":
    check_consistency()