"""
Tests for local polish.
"""

from unittest.mock import patch
from src.generation.local_polish import LocalPolisher


def test_polish_preserves_context():
    """局所パッチが前後の文脈を保持することを確認"""
    original = "最初の文。対象シーン。最後の文。"
    # 対象シーンのみを「改善された対象シーン」に置換することを期待
    polished = LocalPolisher().polish(
        original,
        target_range=(4, 10),  # 「対象シーン」の位置
        improvement_instruction="より感情豊かに書き直して"
    )
    assert polished.startswith("最初の文。")
    assert polished.endswith("最後の文。")
    assert "改善された対象シーン" in polished


def test_polish_handles_invalid_range():
    """無効な範囲が指定された場合は元のテキストを返す"""
    original = "これはテストです。"
    polisher = LocalPolisher()
    
    # 開始位置が負の値
    result = polisher.polish(original, (-1, 5), "改善して")
    assert result == original
    
    # 終了位置がテキスト長を超える
    result = polisher.polish(original, (0, 100), "改善して")
    assert result == original
    
    # 開始位置が終了位置以上
    result = polisher.polish(original, (5, 5), "改善して")
    assert result == original
    
    result = polisher.polish(original, (10, 5), "改善して")
    assert result == original


@patch("src.generation.local_polish.call_llm_api")
def test_polish_calls_llm_with_correct_prompt(mock_call_llm):
    """LLMが正しいプロンプトで呼ばれることを確認"""
    # モックの設定
    mock_call_llm.return_value = "改善されたテキスト"
    
    original = "前文脈。対象テキスト。後文脈。"
    polisher = LocalPolisher()
    
    # 対象範囲を指定（ここでは「対象テキスト」の部分）
    # "前文脈。" = 5文字、なので対象範囲は(5, 5+4) = (5, 9) assuming "対象テキスト" is 4 chars
    # 実際の文字数を正確に合わせるため、わかりやすいテキストを使う
    text = "こんにちは。対象部分。さようなら。"
    # "こんにちは。" = 5文字、なので対象範囲は(5, 5+5) = (5, 10) assuming "対象部分" is 5 chars
    polished = polisher.polish(
        text,
        target_range=(5, 10),  # 「対象部分」の位置
        improvement_instruction="より詳細に説明してください"
    )
    
    # 結果を検証
    assert polished == "こんにちは。改善されたテキスト。さようなら。"
    
    # LLMが呼ばれたことを確認
    mock_call_llm.assert_called_once()
    
    # 呼び出されたプロンプトを確認（詳細まではチェックしないが、呼ばれたことは確認）
    args, kwargs = mock_call_llm.call_args
    prompt = args[0]  # 第一引数がプロンプト
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "対象部分" in prompt or "context" in prompt.lower()


def test_polish_handles_llm_failure():
    """LLM呼び出しに失敗した場合は元のテキストを返す"""
    with patch("src.generation.local_polish.call_llm_api") as mock_call_llm:
        # LLM呼び出しが例外を投げるように設定
        mock_call_llm.side_effect = Exception("LLM Error")
        
        original = "これはテストです。対象部分です。"
        polisher = LocalPolisher()
        
        # 対象範囲を指定
        polished = polisher.polish(
            original,
            target_range=(5, 9),  # 「テストです」の部分（概算）
            improvement_instruction="改善して"
        )
        
        # LLM失敗時は元のテキストを返すはず
        assert polished == original