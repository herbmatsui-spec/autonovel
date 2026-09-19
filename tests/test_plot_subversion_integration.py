# tests/test_plot_subversion_integration.py
import pytest
import sys
sys.path.insert(0, '.')

from src.models.plot import PlotEpisode
from src.models.subversion import SubversionEngine


class TestPlotSubversionIntegration:
    def test_subversion_attribute_exists(self):
        ep = PlotEpisode(ep_num=1)
        assert hasattr(ep, "subversion")
        assert isinstance(ep.subversion, SubversionEngine)

    def test_roundtrip_schedule(self):
        ep = PlotEpisode(ep_num=1)
        ep.subversion.plan_schedule(15)
        dumped = ep.model_dump()
        restored = PlotEpisode.model_validate(dumped)
        assert [p.trigger_ep for p in ep.subversion.schedule] == \
               [p.trigger_ep for p in restored.subversion.schedule]

    def test_sub_model_names_includes_subversion(self):
        assert "subversion" in PlotEpisode._get_sub_model_names()

    def test_unwrap_routing(self):
        data = {"ep_num": 1, "subversion": {"interval": 5, "enabled": True}}
        ep = PlotEpisode.model_validate(data)
        assert ep.subversion.interval == 5
        assert ep.subversion.enabled is True

    def test_extra_engines_fallback(self):
        data = {"ep_num": 1, "subversion_engine": {"interval": 4}}
        ep = PlotEpisode.model_validate(data)
        # extra_engines に吸収される
        assert hasattr(ep, "subversion")
        assert "subversion_engine" in ep.extra_engines

    def test_subversion_engine_functionality(self):
        """SubversionEngine の基本機能が PlotEpisode 経由で動くこと"""
        ep = PlotEpisode(ep_num=1)
        ep.subversion.plan_schedule(10)
        
        # schedule が生成される
        assert len(ep.subversion.schedule) > 0
        
        # apply_to_arc が動く
        class MockArc:
            thematic_milestone = ""
        arc = MockArc()
        ep.subversion.apply_to_arc(arc, 3)
        assert "裏切り" in arc.thematic_milestone
        
        # apply_to_beat が動く
        class MockBeat:
            mission = ""
            visual_scene_focus = ""
            tension_target = 0.5
        beat = MockBeat()
        ep.subversion.apply_to_beat(beat, 3)
        assert "裏切り" in beat.mission
        assert "代償の可視化" in beat.visual_scene_focus
        assert beat.tension_target == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])