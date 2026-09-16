from src.services.nlp.tense_analyzer import TenseAnalyzer

def test_tense_analyzer_ratio():
    analyzer = TenseAnalyzer()
    text = "風が吹いた。空を見上げた。歩き出す。雨が降り始めた。"
    result = analyzer.analyze(text)
    assert "past_ratio" in result
    assert "present_ratio" in result
    assert result["past_ratio"] > 0.5
