import sys

# Add the workspace to path
sys.path.append(r"I:\claude2")

try:
    from backend.engine import OutputSanitizer
    print(f"OutputSanitizer from engine: {OutputSanitizer}")
    print(f"Has format_validation_error: {hasattr(OutputSanitizer, 'format_validation_error')}")
    if hasattr(OutputSanitizer, 'format_validation_error'):
        print(f"Value: {OutputSanitizer.format_validation_error}")

    from backend.sanitizer import OutputSanitizer as OriginalSanitizer
    print(f"OutputSanitizer from sanitizer: {OriginalSanitizer}")
    print(f"Are they the same? {OutputSanitizer is OriginalSanitizer}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

