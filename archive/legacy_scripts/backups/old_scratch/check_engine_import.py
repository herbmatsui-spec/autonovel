
import os
import sys

sys.path.append(os.getcwd())

from backend import engine
from backend.sanitizer import OutputSanitizer as OriginalSanitizer


def test():
    print(f"engine.OutputSanitizer: {engine.OutputSanitizer}")
    print(f"OriginalSanitizer: {OriginalSanitizer}")

    if hasattr(engine.OutputSanitizer, 'format_validation_error'):
        print("engine.OutputSanitizer HAS format_validation_error")
    else:
        print("engine.OutputSanitizer DOES NOT HAVE format_validation_error")

    if hasattr(OriginalSanitizer, 'format_validation_error'):
        print("OriginalSanitizer HAS format_validation_error")
    else:
        print("OriginalSanitizer DOES NOT HAVE format_validation_error")

    import inspect
    print(f"engine.OutputSanitizer source file: {inspect.getfile(engine.OutputSanitizer)}")
    print(f"OriginalSanitizer source file: {inspect.getfile(OriginalSanitizer)}")

if __name__ == "__main__":
    test()

