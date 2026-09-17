# -*- coding: utf-8 -*-
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

try:
    from src.services import conflict_report_service
    print("conflict_report_service:", conflict_report_service.__file__)
except Exception as e:
    print("IMPORT ERROR:", e)

try:
    from src.services import audit_service
    print("audit_service:", audit_service.__file__)
except Exception as e:
    print("IMPORT ERROR audit:", e)

try:
    from src.services import book_score_service
    print("book_score_service:", book_score_service.__file__)
except Exception as e:
    print("IMPORT ERROR book_score:", e)
