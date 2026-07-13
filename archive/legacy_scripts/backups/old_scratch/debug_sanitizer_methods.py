import logging

from backend.sanitizer import OutputSanitizer

logging.basicConfig(level=logging.INFO)
print(f"OutputSanitizer class: {OutputSanitizer}")
print(f"Has attribute 'format_validation_error': {hasattr(OutputSanitizer, 'format_validation_error')}")
if hasattr(OutputSanitizer, 'format_validation_error'):
    print(f"Attribute value: {OutputSanitizer.format_validation_error}")
else:
    print("Methods available in OutputSanitizer:")
    print([m for m in dir(OutputSanitizer) if not m.startswith('__')])

