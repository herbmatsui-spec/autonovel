import sys
sys.path.insert(0, 'E:\\hhh')
from src.services.exporters.base import sanitize_for_narou
print(repr(sanitize_for_narou("^[注釈]")))
print(repr(sanitize_for_narou("![alt](url)")))
print(repr(sanitize_for_narou("|漢字《かんじ》|")))