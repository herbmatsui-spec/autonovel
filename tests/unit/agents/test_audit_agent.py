from src.agents.audit import PlotIntegrityMonitor

def test_audit_agent_detect_contradiction():
    monitor = PlotIntegrityMonitor()
    characters = {"アリス": {"status": "死亡"}}
    scene_text = "アリスは笑顔でリンゴを食べた。"

    issues = monitor.check_scene(scene_text, characters)
    assert len(issues) >= 1
    assert any("死亡" in str(i) for i in issues)
