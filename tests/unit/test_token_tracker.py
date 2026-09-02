from src.services.token_tracker import TokenTracker


def test_token_tracker_lifecycle():
    """TokenTracker の計測ライフサイクルと集計の検証。"""
    tracker = TokenTracker()
    tracker.start()
    assert tracker.start_time is not None

    tracker.add_usage(input_tokens=100, output_tokens=200, ep_num=1)
    tracker.add_usage(input_tokens=50, output_tokens=50, ep_num=2)
    tracker.increment_episode_count()
    tracker.increment_episode_count()

    assert tracker.input_tokens == 150
    assert tracker.output_tokens == 250
    assert tracker.total_tokens == 400
    assert tracker.episode_count == 2
    assert len(tracker.episode_usages) == 2

    tracker.stop()
    assert tracker.end_time is not None

    report = tracker.get_report()
    assert report.total_tokens == 400
    assert report.input_tokens == 150
    assert report.output_tokens == 250
