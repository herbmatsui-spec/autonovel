import pytest
from src.services.nlp.tense_analyzer import TenseContextAnalyzer

def test_tense_analyzer_ratio():
    analyzer = TenseContextAnalyzer()
    text = "風が吹いた。空を見上げた。歩き出す。雨が降り始めた。"
    result = analyzer.analyze_paragraph(text)
    assert result.past_ratio > 0.5
