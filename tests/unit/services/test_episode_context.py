import pytest
from src.services.episode_context import EpisodeContextBuilder

def test_init():
    builder = EpisodeContextBuilder()
    assert builder._episode_history == []

def test_build_context_first_episode():
    builder = EpisodeContextBuilder()
    context = builder.build_context(book_id=1, ep_num=1)
    assert context["book_id"] == 1
    assert context["ep_num"] == 1
    assert context["is_first"] == True
    assert context["is_last"] == False
    assert context["target_word_count"] == 3000
    assert "previous_episode" not in context  # Because previous_episode is None and is_first=True
    assert len(builder._episode_history) == 1
    assert builder._episode_history[0]["ep_num"] == 1
    assert builder._episode_history[0]["context"] == context

def test_build_context_with_previous_episode():
    builder = EpisodeContextBuilder()
    previous = {
        "title": "前話のタイトル",
        "ending": "前話の結末",
        "summary": "前話のあらすじ",
        "key_events": ["イベント1", "イベント2"]
    }
    context = builder.build_context(book_id=1, ep_num=2, previous_episode=previous)
    assert context["book_id"] == 1
    assert context["ep_num"] == 2
    assert context["is_first"] == False
    assert context["is_last"] == False
    assert context["target_word_count"] == 3000
    assert "previous_episode" in context
    assert context["previous_episode"]["title"] == "前話のタイトル"
    assert context["previous_episode"]["ending"] == "前話の結末"
    assert context["previous_episode"]["summary"] == "前話のあらすじ"
    assert context["previous_episode"]["key_events"] == ["イベント1", "イベント2"]
    # History should have one entry (the current context)
    assert len(builder._episode_history) == 1
    assert builder._episode_history[0]["ep_num"] == 2
    assert builder._episode_history[0]["context"] == context

def test_build_context_without_previous_episode_not_first():
    builder = EpisodeContextBuilder()
    # First, add a dummy history to simulate previous episode
    builder._episode_history = [{"ep_num": 1, "context": {"ep_num": 1, "book_id": 1, "is_first": True, "is_last": False, "target_word_count": 3000}}]
    # Now build for ep_num=2 without providing previous_episode
    context = builder.build_context(book_id=1, ep_num=2)
    assert context["book_id"] == 1
    assert context["ep_num"] == 2
    assert context["is_first"] == False
    assert context["previous_episode"] is not None
    # The previous_episode should be derived from history
    assert context["previous_episode"]["title"] == ""
    assert context["previous_episode"]["ending"] == ""
    assert context["previous_episode"]["summary"] == ""
    # After building, history should have two entries
    assert len(builder._episode_history) == 2
    assert builder._episode_history[1]["ep_num"] == 2

def test_add_to_history_and_limit():
    builder = EpisodeContextBuilder()
    # Add 11 episodes
    for i in range(1, 12):
        builder._add_to_history(i, {"ep_num": i})
    assert len(builder._episode_history) == 10  # Should keep only last 10
    assert builder._episode_history[0]["ep_num"] == 2  # First should be ep_num=2
    assert builder._episode_history[-1]["ep_num"] == 11

def test_get_last_episode_summary_empty():
    builder = EpisodeContextBuilder()
    summary = builder._get_last_episode_summary()
    assert summary == {"title": "", "ending": "", "summary": ""}

def test_get_last_episode_summary_with_data():
    builder = EpisodeContextBuilder()
    # Manually set history
    builder._episode_history = [
        {"ep_num": 1, "context": {"ep_num": 1, "book_id": 1, "is_first": True, "is_last": False, "target_word_count": 3000, "previous_episode": {"title": "前話タイトル", "ending": "前話結末", "summary": "前話あらすじ"}}},
        {"ep_num": 2, "context": {"ep_num": 2, "book_id": 1, "is_first": False, "is_last": False, "target_word_count": 3000}},
    ]
    summary = builder._get_last_episode_summary()
    # The last context is for ep_num=2, its context does not have previous_episode, so we look at its context's previous_episode? Actually _get_last_episode_summary returns the previous_episode from the last context's context.
    # The last context's context (ep_num=2) does not have a "previous_episode" key, so it returns empty strings.
    # But wait, the history we set: the first element has previous_episode, the second does not.
    # The last element is the second, so summary should be empty.
    assert summary == {"title": "", "ending": "", "summary": ""}
    # Let's instead set the second element to have a previous_episode in its context.
    builder._episode_history = [
        {"ep_num": 1, "context": {"ep_num": 1, "book_id": 1, "is_first": True, "is_last": False, "target_word_count": 3000}},
        {"ep_num": 2, "context": {"ep_num": 2, "book_id": 1, "is_first": False, "is_last": False, "target_word_count": 3000, "previous_episode": {"title": "前々話タイトル", "ending": "前々話結末", "summary": "前々話あらすじ"}}},
    ]
    summary = builder._get_last_episode_summary()
    assert summary["title"] == "前々話タイトル"
    assert summary["ending"] == "前々話結末"
    assert summary["summary"] == "前々話あらすじ"

def test_get_history():
    builder = EpisodeContextBuilder()
    builder._episode_history = [{"ep_num": 1, "context": {}}, {"ep_num": 2, "context": {}}]
    history = builder.get_history()
    assert len(history) == 2
    assert history[0]["ep_num"] == 1
    assert history[1]["ep_num"] == 2
    # Ensure it's a copy
    history.append({"ep_num": 3, "context": {}})
    assert len(builder._episode_history) == 2  # Original unchanged

def test_clear_history():
    builder = EpisodeContextBuilder()
    builder._episode_history = [{"ep_num": 1, "context": {}}]
    builder.clear_history()
    assert builder._episode_history == []

def test_set_final_episode():
    builder = EpisodeContextBuilder()
    # Create three episodes using build_context to ensure they have the expected keys
    ctx1 = builder.build_context(book_id=1, ep_num=1)
    ctx2 = builder.build_context(book_id=1, ep_num=2)
    ctx3 = builder.build_context(book_id=1, ep_num=3)
    # Manually set history to these contexts
    builder._episode_history = [
        {"ep_num": 1, "context": ctx1},
        {"ep_num": 2, "context": ctx2},
        {"ep_num": 3, "context": ctx3},
    ]
    builder.set_final_episode(2)
    assert builder._episode_history[0]["context"]["is_last"] == False
    assert builder._episode_history[1]["context"]["is_last"] == True
    assert builder._episode_history[2]["context"]["is_last"] == False