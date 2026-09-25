import pytest
from src.config.commercial_beat_sheet import COMMERCIAL_40EP_BEATS, get_beat_for_episode
from src.models.beat_sheet import EpisodeBeat


def test_episode_beat_with_foreshadowing_contract():
    """EpisodeBeatに伏線契約IDリストを付与して正常に生成・検証できること"""
    beat = EpisodeBeat(
        ep_num=15,
        phase="第1の試練・勢力拡大",
        mission="ギルド長との対立と真の敵の正体判明",
        tension_target=0.8,
        visual_scene_focus="ギルドの紋章を叩き割る主人公の冷笑",
        target_foreshadowing_ids=[101, 102],
    )
    assert beat.ep_num == 15
    assert beat.target_foreshadowing_ids == [101, 102]
    # 空リストのデフォルト動作
    beat_empty = EpisodeBeat(
        ep_num=1,
        phase="開幕フック",
        mission="追放と覚醒",
        tension_target=0.9,
        visual_scene_focus="大雨の中の覚醒",
    )
    assert beat_empty.target_foreshadowing_ids == []


def test_commercial_40ep_beats_coverage():
    """1話から40話まで抜け漏れなくビートが定義されていること"""
    for ep in range(1, 41):
        beat_def = get_beat_for_episode(ep)
        assert beat_def is not None
        assert "phase" in beat_def
        assert "directive" in beat_def
        assert "foreshadowing_directive" in beat_def
        assert "target_scopes" in beat_def

    # 境界値テスト
    assert get_beat_for_episode(1)["phase"] == "開幕フック"
    assert get_beat_for_episode(3)["phase"] == "開幕フック"
    assert get_beat_for_episode(4)["phase"] == "初期成功・拠点確立"
    assert get_beat_for_episode(10)["phase"] == "初期成功・拠点確立"
    assert get_beat_for_episode(25)["phase"] == "Midpoint・大転換"
    assert get_beat_for_episode(35)["phase"] == "クライマックス決戦"
    assert get_beat_for_episode(40)["phase"] == "凱旋・第1巻結び"
