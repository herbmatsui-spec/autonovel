# -*- coding: utf-8 -*-
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

import src.services.semantic_cache as m

names = [n for n in dir(m) if not n.startswith("_")]
print("exports:", names)
