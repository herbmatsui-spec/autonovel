
import os
import sys

from pydantic import BaseModel, ValidationError

# Add current directory to path to import local modules
sys.path.insert(0, os.getcwd())

from backend.sanitizer import OutputSanitizer


class TestModel(BaseModel):
    name: str
    age: int

def test_validation_formatting():
    print("Testing OutputSanitizer.format_validation_error...")
    try:
        # Trigger a validation error
        TestModel(name=123) # age is missing, name is wrong type
    except ValidationError as ve:
        formatted = OutputSanitizer.format_validation_error(ve)
        print("Formatted Error Message:")
        print(formatted)
        assert "name" in formatted
        assert "age" in formatted
        print("Test Passed!")

if __name__ == "__main__":
    test_validation_formatting()

