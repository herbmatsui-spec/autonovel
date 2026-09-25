import tomli

def test_coverage_threshold_meets_phase1_goal():
    """Phase 1 ではカバレッジ閾値を維持・向上させる"""
    with open("pyproject.toml", "rb") as f:
        config = tomli.load(f)
    assert config["tool"]["coverage"]["report"]["fail_under"] >= 55