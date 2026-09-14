import pytest
from src.agents.erotic.continuity import EroticContinuityTracker

def test_continuity_state_transition():
    tracker = EroticContinuityTracker()
    tracker.update_character_state("ヒロイン", {"clothing": "水着", "pose": "仰向け"})
    
    state = tracker.get_character_state("ヒロイン")
    assert state["clothing"] == "水着"
    assert state["pose"] == "仰向け"