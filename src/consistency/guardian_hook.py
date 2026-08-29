"""consistency/guardian_hook.py - LLM Guardian への注入フック"""
from typing import Optional

from src.consistency.engine import ConsistencyEngine
from src.consistency.findings import Finding
from src.consistency.checkers.base import CheckContext
from src.consistency.checkers import get_default_checkers
from src.consistency.filters import filter_intentional
from src.consistency.dismissed_store import get_all_dismissals
from src.consistency.injector import format_findings_for_prompt


def get_consistency_prompt_injection(
    book_id: int, branch_id: int = 1, ep_num: Optional[int] = None
) -> str:
    """
    整合性チェックを実行し、LLM Guardian / 章執筆プロンプトに注入する文字列を返す。
    空文字列が返る場合は注入不要。
    """
    engine = ConsistencyEngine(get_default_checkers())
    context = CheckContext(book_id=book_id, branch_id=branch_id, ep_num=ep_num)
    findings = engine.run(context)
    dismissed = get_all_dismissals(book_id, branch_id)
    filtered = filter_intentional(findings, set(dismissed.keys()))
    if not filtered:
        return ""
    return format_findings_for_prompt(filtered)