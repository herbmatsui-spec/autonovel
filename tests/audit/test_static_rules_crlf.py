"""
StaticRuleAuditor の改行コード正規化と位置精度リグレッションテスト (Step 8)
"""

import pytest
from src.audit.static_rules import StaticRuleAuditor


def test_static_rules_crlf_line_start_forbidden_offset():
    """Windows改行(\\r\\n)を含むテキストでも行頭禁則文字の位置が正確であること"""
    auditor = StaticRuleAuditor()
    text = "第1章　旅立ち\r\n、これは禁則の行頭です。\r\n正常な段落です。"

    issues = auditor.audit(text)
    forbidden_issues = [i for i in issues if i.type == "line_start_forbidden_punct"]

    assert len(forbidden_issues) == 1
    issue = forbidden_issues[0]

    # 正規化後のテキスト:
    # "第1章　旅立ち\n、これは禁則の行頭です。\n正常な段落です。"
    # "第1章　旅立ち\n" は 8文字 (第=0, 1=1, 章=2, 　=3, 旅=4, 立=5, ち=6, \n=7)
    # したがって次の行の "、" は offset 8
    assert issue.location == (8, 9)


def test_static_rules_empty_text():
    """空文字列でparagraph_count_insufficientを返すこと"""
    auditor = StaticRuleAuditor()
    issues = auditor.audit("")
    assert any(i.type == "paragraph_count_insufficient" for i in issues)


def test_static_rules_title_length_exceeded():
    """タイトル文字数超過が正確に検出されること"""
    auditor = StaticRuleAuditor()
    long_title = "あ" * 105 + "\n本文です。"
    issues = auditor.audit(long_title)
    title_issues = [i for i in issues if i.type == "title_length_exceeded"]
    assert len(title_issues) == 1
    assert title_issues[0].location == (0, 105)
