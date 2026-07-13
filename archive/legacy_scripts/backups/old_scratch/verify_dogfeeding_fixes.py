import inspect
import sys
from pathlib import Path

root = Path(r"i:\claude2")
sys.path.insert(0, str(root))

from backend.engine_context import ContextManager
from backend.engine_utils import GenreClassifier


def test_signature():
    print("Verifying get_optimal_context_split signature...")
    sig = inspect.signature(ContextManager.get_optimal_context_split)
    print(f"Signature: {sig}")
    params = list(sig.parameters.values())
    last_param = params[-1]
    if last_param.name == "narrative_controller" and last_param.default != inspect.Parameter.empty:
        print("Success: narrative_controller is now optional!")
    else:
        print(f"Failure: narrative_controller is not optional. Default: {last_param.default}")

def test_style_key_access():
    print("\nVerifying robust style_key access...")
    class MockBook:
        def __init__(self, style_dna, genre):
            self.style_dna = style_dna
            self.genre = genre
        @property
        def style_key(self):
            if isinstance(self.style_dna, dict):
                return self.style_dna.get("mode", "default")
            return "default"

    # Test with object that HAS style_key property
    book_obj = MockBook({"mode": "serious"}, "fantasy")
    profile = GenreClassifier.classify(getattr(book_obj, "style_key", "default"), book_obj.genre)
    print(f"Access via getattr (object): {profile}")

    # Test with object that DOES NOT have style_key property
    class BadBook:
        def __init__(self):
            self.genre = "fantasy"

    bad_book = BadBook()
    profile = GenreClassifier.classify(getattr(bad_book, "style_key", "default"), bad_book.genre)
    print(f"Access via getattr (bad object): {profile}")

if __name__ == "__main__":
    test_signature()
    test_style_key_access()

