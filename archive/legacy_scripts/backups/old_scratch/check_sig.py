import inspect
import sys
from pathlib import Path

root = Path(r"i:\claude2")
sys.path.insert(0, str(root))

from backend.engine_context import ContextManager


def check_signature():
    sig = inspect.signature(ContextManager.get_optimal_context_split)
    print(f"Signature: {sig}")
    print(f"Parameters: {list(sig.parameters.keys())}")

if __name__ == "__main__":
    check_signature()

