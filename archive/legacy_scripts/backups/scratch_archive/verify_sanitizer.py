import os
import sys

sys.path.append(os.getcwd())

from backend.sanitizer import OutputSanitizer


def test_sanitizer():
    raw_text = """
[PLAN]
This is the plan. Avoid using word 'happy'.
[/PLAN]

[STORY]
Alvin was walking in the dark forest.
[/STORY]
"""
    metadata, content = OutputSanitizer.extract_content_and_metadata(raw_text)
    print(f"Metadata: {metadata}")
    print(f"Content: {content}")

    assert "thought_process" in metadata
    assert metadata["thought_process"] == "This is the plan. Avoid using word 'happy'."
    assert content == "Alvin was walking in the dark forest."
    print("Sanitizer test passed!")

if __name__ == "__main__":
    test_sanitizer()

