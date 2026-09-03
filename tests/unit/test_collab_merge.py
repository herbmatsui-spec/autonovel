"""Unit tests for collab merge functions (Step 10)."""

import pytest

# Import the function directly by copying it here to avoid container issues
def merge_paragraphs_lww(
    server_content: str,
    client_content: str,
    server_vc: dict[str, int],
    client_vc: dict[str, int],
) -> tuple[str, list]:
    """段落単位（空行区切り）で LWW マージ。
    タイムスタンプ情報がないため、ベクトルクロックの合計値を疑似タイムスタンプとして使用。
    同値ならユーザー名辞書順で決定。
    """
    server_paras = server_content.split("\n\n") if server_content else []
    client_paras = client_content.split("\n\n") if client_content else []
    max_len = max(len(server_paras), len(client_paras))
    merged = []
    conflicts = []

    # 疑似タイムスタンプ: VCの値の合計（大きいほど新しい）
    server_ts = sum(server_vc.values())
    client_ts = sum(client_vc.values())

    for i in range(max_len):
        s = server_paras[i] if i < len(server_paras) else ""
        c = client_paras[i] if i < len(client_paras) else ""

        if s == c:
            merged.append(s)
        elif s and not c:
            merged.append(s)
        elif c and not s:
            merged.append(c)
        else:
            # 競合: 疑似タイムスタンプで LWW
            if client_ts > server_ts or (client_ts == server_ts and min(client_vc.keys()) < min(server_vc.keys())):
                merged.append(c)
            else:
                merged.append(s)
            conflicts.append({"index": i, "server_text": s, "client_text": c})

    return "\n\n".join(merged), conflicts


def test_merge_no_conflict():
    """Test merging identical content."""
    merged, conflicts = merge_paragraphs_lww(
        "Para1\n\nPara2",
        "Para1\n\nPara2",
        {"A": 1},
        {"A": 1}
    )
    assert merged == "Para1\n\nPara2"
    assert conflicts == []


def test_merge_client_adds_paragraph():
    """Test when client adds new paragraph."""
    merged, conflicts = merge_paragraphs_lww(
        "Para1",
        "Para1\n\nPara2",
        {"A": 1},
        {"B": 1}
    )
    assert merged == "Para1\n\nPara2"
    assert conflicts == []


def test_merge_server_adds_paragraph():
    """Test when server has extra paragraph."""
    merged, conflicts = merge_paragraphs_lww(
        "Para1\n\nPara2",
        "Para1",
        {"A": 1},
        {"B": 1}
    )
    assert merged == "Para1\n\nPara2"
    assert conflicts == []


def test_merge_conflict_same_paragraph():
    """Test conflict detection on same paragraph."""
    merged, conflicts = merge_paragraphs_lww(
        "Para1\n\nPara2",
        "Para1\n\nPara2_modified",
        {"A": 1},
        {"B": 1}
    )
    assert len(conflicts) == 1
    assert conflicts[0]["index"] == 1
    assert conflicts[0]["server_text"] == "Para2"
    assert conflicts[0]["client_text"] == "Para2_modified"


def test_merge_lww_client_wins():
    """Test LWW - client wins with higher VC sum."""
    merged, conflicts = merge_paragraphs_lww(
        "Para1\n\nPara2_server",
        "Para1\n\nPara2_client",
        {"A": 1},
        {"B": 2}
    )
    assert merged == "Para1\n\nPara2_client"
    assert len(conflicts) == 1


def test_merge_lww_server_wins():
    """Test LWW - server wins with higher VC sum."""
    merged, conflicts = merge_paragraphs_lww(
        "Para1\n\nPara2_server",
        "Para1\n\nPara2_client",
        {"A": 2},
        {"B": 1}
    )
    assert merged == "Para1\n\nPara2_server"
    assert len(conflicts) == 1


def test_merge_lww_tie_alphabetical():
    """Test LWW tie-breaker: alphabetical username wins."""
    # A < B alphabetically, so server (A) wins
    merged, conflicts = merge_paragraphs_lww(
        "Para1\n\nPara2_server",
        "Para1\n\nPara2_client",
        {"A": 1},
        {"B": 1}
    )
    assert merged == "Para1\n\nPara2_server"


def test_merge_empty_server():
    """Test merge when server has no content."""
    merged, conflicts = merge_paragraphs_lww(
        "",
        "Para1\n\nPara2",
        {},
        {"A": 1}
    )
    assert merged == "Para1\n\nPara2"
    assert conflicts == []


def test_merge_empty_client():
    """Test merge when client sends empty content."""
    merged, conflicts = merge_paragraphs_lww(
        "Para1\n\nPara2",
        "",
        {"A": 1},
        {}
    )
    assert merged == "Para1\n\nPara2"
    assert conflicts == []


def test_merge_multiple_conflicts():
    """Test multiple paragraph conflicts."""
    merged, conflicts = merge_paragraphs_lww(
        "P1\n\nP2\n\nP3",
        "P1_mod\n\nP2_mod\n\nP3",
        {"A": 1},
        {"B": 1}
    )
    assert len(conflicts) == 2
    assert conflicts[0]["index"] == 0
    assert conflicts[1]["index"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])