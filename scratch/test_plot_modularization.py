
import os
import sys

# Ensure models can be imported
sys.path.append(os.getcwd())

from models.plot import DramaEpisode, MysteryEpisode, PlotEpisode, plot_episode_factory


def test_flat_data_routing():
    print("Testing flat data routing...")
    flat_data = {
        "ep_num": 1,
        "title": "The First Mystery",
        "tension": 50,
        "tension_delta": 10,
        "knowledge_delta": 0.3,
        "unknown_engine_value": "Something New",
        "script_content": "Once upon a time..."
    }

    # Test with default PlotEpisode
    ep = PlotEpisode(**flat_data)

    # Verify core_info (the critical fix)
    assert ep.core_info.ep_num == 1, f"Expected ep_num 1, got {ep.core_info.ep_num}"
    assert ep.core_info.title == "The First Mystery", f"Expected title 'The First Mystery', got {ep.core_info.title}"

    # Verify analytics
    assert ep.analytics.tension == 50, f"Expected tension 50, got {ep.analytics.tension}"

    # Verify extra_engines
    assert ep.extra_engines.get("unknown_engine_value") == "Something New", "Expected unknown_engine_value in extra_engines"

    # Verify generic fields
    assert ep.script_content == "Once upon a time...", "Expected script_content to be preserved"

    print("OK: Flat data routing verified.")

def test_factory_specialization():
    print("Testing factory specialization...")
    data = {"ep_num": 2, "title": "Mystery Night"}

    mystery_ep = plot_episode_factory("mystery", **data)
    assert isinstance(mystery_ep, MysteryEpisode), f"Expected MysteryEpisode, got {type(mystery_ep)}"

    drama_ep = plot_episode_factory("drama", **data)
    assert isinstance(drama_ep, DramaEpisode), f"Expected DramaEpisode, got {type(drama_ep)}"

    print("OK: Factory specialization verified.")

def test_nested_data_preservation():
    print("Testing nested data preservation...")
    nested_data = {
        "core_info": {"ep_num": 3, "title": "Nested Title"},
        "analytics": {"tension": 70},
        "script_content": "Nested content"
    }

    ep = PlotEpisode(**nested_data)
    assert ep.core_info.ep_num == 3
    assert ep.analytics.tension == 70
    assert ep.script_content == "Nested content"

    print("OK: Nested data preservation verified.")

if __name__ == "__main__":
    try:
        test_flat_data_routing()
        test_factory_specialization()
        test_nested_data_preservation()
        print("\nALL TESTS PASSED SUCCESSFULLY")
    except AssertionError as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

