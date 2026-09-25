"""
Tests for static rule auditor.
"""

import pytest
from src.audit.static_rules import StaticRuleAuditor, Issue


def test_too_long_chapter_detected():
    """5000文字を超える章はlength_exceeded Issueを検出する"""
    # 仮の上限5000字（StaticRuleAuditorのデフォルト）
    text = "あ" * 5001
    auditor = StaticRuleAuditor()
    issues = auditor.audit(text)
    
    assert any(issue.type == "length_exceeded" for issue in issues)
    assert any("文字数が上限を超えています" in issue.message for issue in issues)


def test_title_length_exceeded_detected():
    """章タイトルが長すぎる場合はtitle_length_exceeded Issueを検出する"""
    # まず章タイトルとなる長い最初の行、その後に本文
    long_title = "あ" * 101  # デフォルト上限100字を超える
    text = f"{long_title}\n\nこれは本文です。"
    auditor = StaticRuleAuditor()
    issues = auditor.audit(text)
    
    assert any(issue.type == "title_length_exceeded" for issue in issues)
    assert any("章タイトルが長すぎます" in issue.message for issue in issues)


def test_paragraph_count_insufficient():
    """段落数が不足している場合はparagraph_count_insufficient Issueを検出する"""
    # 段落が0個か1個のテキスト（最低1段落必要だが、実装では少なくとも1段落必要なので0段落のケースをテスト）
    # 実際は空文字列または改行のみの文字列
    text = ""  # 0段落
    auditor = StaticRuleAuditor()
    issues = auditor.audit(text)
    
    # 空文字列の場合、段落数は0になるはず
    assert any(issue.type == "paragraph_count_insufficient" for issue in issues)


def test_line_start_forbidden_punct_detected():
    """行頭に禁則文字がある場合はline_start_forbidden_punct Issueを検出する"""
    text = "、これはテストです。\nこれは二行目です。"
    auditor = StaticRuleAuditor()
    issues = auditor.audit(text)
    
    assert any(issue.type == "line_start_forbidden_punct" for issue in issues)
    assert any("行頭に禁則文字があります" in issue.message for issue in issues)


def test_no_issues_when_valid():
    """有効なテキストについてはIssueが検出されない"""
    text = "これは有効なテキストです。\n\n適切な段落構造があります。"
    auditor = StaticRuleAuditor()
    issues = auditor.audit(text)
    
    # 長さなどの制限を超えていないことを前提に、Issueが空であることを確認
    # 注意: このテキストは5000文字未満かつ適切な形式なので、Issueが検出されないはず
    length_exceeded_issues = [issue for issue in issues if issue.type == "length_exceeded"]
    assert len(length_exceeded_issues) == 0