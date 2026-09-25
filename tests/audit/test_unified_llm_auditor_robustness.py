"""
UnifiedLLMAuditor のJSON抽出堅牢化とリグレッション防止テスト (Step 9)
"""

import pytest
from unittest.mock import patch
from src.audit.unified_llm_auditor import UnifiedLLMAuditor, Issue


@patch("src.audit.unified_llm_auditor.call_llm_api")
def test_auditor_parses_markdown_json_codeblock(mock_call):
    """```json ... ``` で囲まれたレスポンスから正常にIssueを抽出できること"""
    mock_call.return_value = """
承知しました。小説の品質を評価しました。
```json
[
  {
    "type": "plot_inconsistency",
    "message": "第1話で昼だったシーンが直後に夜になっています",
    "location": [50, 120],
    "suggestion": "時間経過の描写を追加してください"
  }
]
```
以上が指摘事項です。
"""
    auditor = UnifiedLLMAuditor()
    issues = auditor.audit("テストテキスト")

    assert len(issues) == 1
    assert issues[0].type == "plot_inconsistency"
    assert "昼だったシーン" in issues[0].message
    assert issues[0].location == (50, 120)
    assert issues[0].suggestion == "時間経過の描写を追加してください"


@patch("src.audit.unified_llm_auditor.call_llm_api")
def test_auditor_parses_raw_json_with_surrounding_text(mock_call):
    """コードブロックなしで前後にテキストがある場合でも配列部分を抽出できること"""
    mock_call.return_value = """
以下が評価結果です：
[
  {"type": "character_appeal", "message": "主人公の動機が不明確です"}
]
修正をご検討ください。
"""
    auditor = UnifiedLLMAuditor()
    issues = auditor.audit("テストテキスト")

    assert len(issues) == 1
    assert issues[0].type == "character_appeal"
    assert issues[0].location is None


@patch("src.audit.unified_llm_auditor.call_llm_api")
def test_auditor_handles_broken_text_gracefully(mock_call):
    """完全に壊れたテキストでもクラッシュせず空リストを返すこと"""
    mock_call.return_value = "すみません、評価できませんでした。"
    auditor = UnifiedLLMAuditor()
    issues = auditor.audit("テストテキスト")
    assert issues == []


def test_auditor_empty_input():
    """空入力時はLLMを呼ばずに空リストを返すこと"""
    auditor = UnifiedLLMAuditor()
    assert auditor.audit("") == []
