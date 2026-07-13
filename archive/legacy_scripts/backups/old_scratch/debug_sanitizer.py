
import os
import sys

sys.path.insert(0, os.getcwd())
try:
    from backend.sanitizer import OutputSanitizer
    print(f"OutputSanitizer found in {OutputSanitizer.__module__}")
    print(f"File: {sys.modules['sanitizer'].__file__}")
    print(f"Attributes: {dir(OutputSanitizer)}")
    print(f"Has format_validation_error: {hasattr(OutputSanitizer, 'format_validation_error')}")
except Exception as e:
    print(f"Error: {e}")

