import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.backend.sanitizer import OutputSanitizer

r = OutputSanitizer.extract_content_and_metadata('{"title": "T", "score": 5}')
print("META:", repr(r[0]))
print("STORY:", repr(r[1]))
