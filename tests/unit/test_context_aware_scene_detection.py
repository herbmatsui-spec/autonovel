from src.services.compression.layer4_trimming import Layer4SceneTrimmer
from src.services.compression.models import SceneFlowHistory

def test_scene_context_aware_detection_handles_post_combat_meeting():
    trimmer = Layer4SceneTrimmer()
    # テキストには「魔王」「撃破」などの単語が含まれるが、主目的は「作戦会議・方針策定」
    plot = "魔王を討伐した後の対策会議を行う。今後の領地関税と防衛体制を協議する。"
    history = SceneFlowHistory(
        recent_scene_types=["combat"],
        episode_goal="戦後処理と政治的同盟交渉",
    )
    detected = trimmer.detect_scene_context_aware(plot, scene_flow=history)
    top_scene, prob = detected[0]

    # combat ではなく political または daily が優勢になること
    assert top_scene in ["political", "daily", "general"]
