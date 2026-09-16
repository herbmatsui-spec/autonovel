from src.services.writing_services import clean_writing_response

def test_clean_writing_response_strip_thinking():
    raw = "<thinking>プロットの整理...</thinking>「こんにちは」と彼女は言った。"
    cleaned = clean_writing_response(raw)
    assert "<thinking>" not in cleaned
    assert "「こんにちは」" in cleaned
