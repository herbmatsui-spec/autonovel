import sys
sys.path.insert(0, 'E:\\hhh')
from src.services.exporters.base import sanitize_for_narou
result = sanitize_for_narou("^[注釈]")
print("Result bytes:", result.encode('utf-8'))
print("Expected bytes:", "(注釈)".encode('utf-8'))
print("Are they equal?", result == "(注釈)")