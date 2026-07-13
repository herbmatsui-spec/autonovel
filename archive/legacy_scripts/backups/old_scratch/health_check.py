
import logging
import os
import sys

# Disable logging to keep output clean
logging.basicConfig(level=logging.ERROR)

sys.path.insert(0, os.getcwd())

def check_imports():
    print("Checking imports and basic method existence...")
    try:

        from backend.sanitizer import (
            OutputSanitizer,
            TonePerfector,
            VocabularyOptimizer,
        )

        # Check TonePerfector
        assert hasattr(TonePerfector, 'enforce_tone'), "TonePerfector missing enforce_tone"
        assert hasattr(TonePerfector, 'force_physical_translation'), "TonePerfector missing force_physical_translation"

        # Check VocabularyOptimizer
        assert hasattr(VocabularyOptimizer, 'deduplicate'), "VocabularyOptimizer missing deduplicate"

        # Check OutputSanitizer
        assert hasattr(OutputSanitizer, 'format_validation_error'), "OutputSanitizer missing format_validation_error"
        assert hasattr(OutputSanitizer, 'extract_content_and_metadata'), "OutputSanitizer missing extract_content_and_metadata"

        print("Basic sanity check: PASSED")
    except Exception as e:
        print(f"Sanity check FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_imports()

