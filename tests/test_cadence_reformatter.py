from src.services.cadence_reformatter import CadenceReformatter


def test_cadence_reformatter_repeated_endings():
    """「〜た。」が3回以上連続した場合に自動補正されるか検証"""
    reformatter = CadenceReformatter()
    input_text = "男は走った。敵は追ってきた。恐怖を感じていた。彼は勝利を確信した。"
    reformatted, stats = reformatter.reformat_novel_text(input_text)

    assert stats.total_sentences == 4
    assert stats.repeated_endings_fixed >= 1
    # 「ていた――。」などに補正されているか
    assert "ていた――。" in reformatted or "感じる。" in reformatted


def test_cadence_reformatter_preserves_dialogue():
    """会話文は口調を崩さずにそのまま保持されるか検証"""
    reformatter = CadenceReformatter()
    input_text = "「お前には負けない。絶対に勝つんだ。」\n男はそう宣言した。"
    reformatted, stats = reformatter.reformat_novel_text(input_text)

    assert "「お前には負けない。絶対に勝つんだ。」" in reformatted
