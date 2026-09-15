import pytest
from src.agents.erotic.diversity_scorer import EroticDiversityScorer

def test_diversity_score_calculation():
    scorer = EroticDiversityScorer()
    text = "激しく抱きしめ、囁き、唇を重ねた。"
    score = scorer.calculate_diversity(text)
    assert 0.0 <= score <= 1.0
