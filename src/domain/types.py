from __future__ import annotations

from typing import NewType

# ID Types for strong typing
BookId = NewType("BookId", str)
PlotId = NewType("PlotId", str)
ChapterId = NewType("ChapterId", str)
CharacterId = NewType("CharacterId", str)
BranchId = NewType("BranchId", str)
BibleId = NewType("BibleId", str)
RuleId = NewType("RuleId", str)
AuditId = NewType("AuditId", str)
PromptVersionId = NewType("PromptVersionId", int)
