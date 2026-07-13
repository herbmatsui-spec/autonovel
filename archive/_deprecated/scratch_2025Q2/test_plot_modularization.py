
from models.plot import DramaEpisode, MysteryEpisode, SliceOfLifeEpisode, plot_episode_factory


def test_regression_flat_data():
    print("Testing: Backward compatibility with flat data...")
    # AI-generated style flat dictionary
    flat_data = {
        "ep_num": 1,
        "title": "謎の始まり",
        "one_line_summary": "主人公が奇妙な事件に巻き込まれる",
        "tension": 60,
        "tension_delta": 10,
        "catharsis": 0,
        "is_catharsis": False,
        "knowledge_delta": "0.2",  # String for float testing
        "truth_convergence": 0.1,
        "qol_delta": 5,            # Comfort engine data in a generic PlotEpisode
        "veneration_gain": 0.1,
    }

    # Use default PlotEpisode via factory (generic)
    ep = plot_episode_factory("generic", **flat_data)

    print(f"Debug: ep.core_info.ep_num = {ep.core_info.ep_num}")
    print(f"Debug: ep.analytics.tension = {ep.analytics.tension}")
    print(f"Debug: ep.enigma.knowledge_delta = {ep.enigma.knowledge_delta}")
    print(f"Debug: ep.comfort.qol_delta = {ep.comfort.qol_delta}")

    assert ep.core_info.ep_num == 1, f"Expected 1, got {ep.core_info.ep_num}"
    assert ep.analytics.tension == 60, f"Expected 60, got {ep.analytics.tension}"
    assert ep.enigma.knowledge_delta == 0.2, f"Expected 0.2, got {ep.enigma.knowledge_delta}"
    assert ep.comfort.qol_delta == 5, f"Expected 5, got {ep.comfort.qol_delta}"

    # Test __getattr__ chain
    assert ep.tension == 60
    assert ep.knowledge_delta == 0.2

    # Test serialization back to flat
    serialized = ep.serialize_flat(lambda x: x.model_dump())
    assert serialized["tension"] == 60
    assert serialized["knowledge_delta"] == 0.2
    print("OK: Backward compatibility passed.")

def test_factory_specialization():
    print("Testing: Factory specialization...")
    data = {"ep_num": 2, "title": "推理の時間"}

    mystery = plot_episode_factory("mystery", **data)
    assert isinstance(mystery, MysteryEpisode)
    assert hasattr(mystery, "enigma")
    assert not hasattr(mystery, "comfort")

    sol = plot_episode_factory("slice_of_life", **data)
    assert isinstance(sol, SliceOfLifeEpisode)
    assert hasattr(sol, "comfort")
    assert not hasattr(sol, "enigma")

    drama = plot_episode_factory("drama", **data)
    assert isinstance(drama, DramaEpisode)
    assert hasattr(drama, "enigma")
    assert hasattr(drama, "comfort")
    print("OK: Factory specialization passed.")

def test_extra_engines():
    print("Testing: extra_engines catch-all...")
    data = {
        "ep_num": 3,
        "unknown_battle_score": 99,
        "unexpected_field": "some value"
    }
    ep = plot_episode_factory("generic", **data)

    assert ep.extra_engines["unknown_battle_score"] == 99
    assert ep.extra_engines["unexpected_field"] == "some value"
    # Check __getattr__ fallback
    assert ep.unknown_battle_score == 99
    print("OK: Extra engines catch-all passed.")

def test_wrapper_peeling():
    print("Testing: Wrapper peeling...")
    wrapped_data = {
        "metadata": {
            "ep_num": 4,
            "title": "ラップされたデータ"
        }
    }
    ep = plot_episode_factory("generic", **wrapped_data)
    assert ep.core_info.ep_num == 4
    print("OK: Wrapper peeling passed.")

if __name__ == "__main__":
    try:
        test_regression_flat_data()
        test_factory_specialization()
        test_extra_engines()
        test_wrapper_peeling()
        print("\nALL INTEGRATION TESTS PASSED SUCCESSFULLY")
    except AssertionError as e:
        print(f"\nFAILED: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nERROR: {e}")

