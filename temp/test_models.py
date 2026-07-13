import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

try:
    print("Starting model rebuild test...")
    from models import rebuild_models
    rebuild_models()
    print("✅ rebuild_models() completed successfully.")

    from models import CharacterConceptList
    print(f"✅ CharacterConceptList imported: {CharacterConceptList}")

    print("All models initialized and rebuilt successfully.")
except Exception as e:
    print(f"❌ Error during model initialization: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
