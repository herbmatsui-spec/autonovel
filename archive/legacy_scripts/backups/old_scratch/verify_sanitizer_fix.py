
import os
import sys

sys.path.append(os.getcwd())

from typing import List

from pydantic import BaseModel, ValidationError

from backend.sanitizer import OutputSanitizer


class TestModel(BaseModel):
    name: str
    age: int
    tags: List[str]

def test():
    try:
        # Trigger validation error
        TestModel(name=123, tags="not a list")
    except ValidationError as ve:
        formatted = OutputSanitizer.format_validation_error(ve)
        print("Formatted Error Message:")
        print(formatted)

if __name__ == "__main__":
    test()

