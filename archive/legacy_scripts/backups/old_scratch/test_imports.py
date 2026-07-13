import logging
import sys

logging.basicConfig(level=logging.DEBUG)

try:
    print("sanitizer imported successfully")
except Exception as e:
    print(f"Error importing sanitizer: {e}")
    sys.exit(1)

try:
    print("Classes imported successfully")
except Exception as e:
    print(f"Error importing classes: {e}")
    sys.exit(1)

print("All imports successful")

