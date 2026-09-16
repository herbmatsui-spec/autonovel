from src.backend.routers.hooks import FixRequest
from src.backend.routers.collab import MemberRequest, CommentRequest

def test_hooks_fix_request_validation():
    req = FixRequest(
        api_key="test-api-key",
        ep_num=1
    )
    assert req.api_key == "test-api-key"
    assert req.ep_num == 1

def test_collab_member_request_validation():
    req = MemberRequest(
        user_name="author_b",
        role="editor"
    )
    assert req.user_name == "author_b"
    assert req.role == "editor"

def test_collab_comment_request_validation():
    req = CommentRequest(
        author_name="reviewer_1",
        content="ここをもっとドラマチックに",
        anchor_text="彼は倒れた。"
    )
    assert req.author_name == "reviewer_1"
    assert req.content == "ここをもっとドラマチックに"
    assert req.anchor_text == "彼は倒れた。"
