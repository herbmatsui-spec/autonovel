# scripts/test_plot_subversion_roundtrip.py
import sys
sys.path.insert(0, '.')

from src.models.plot import PlotEpisode

ep = PlotEpisode(ep_num=1)
ep.subversion.plan_schedule(12)
dumped = ep.model_dump()
restored = PlotEpisode.model_validate(dumped)

orig = [p.model_dump() for p in ep.subversion.schedule]
rest = [p.model_dump() for p in restored.subversion.schedule]
assert orig == rest, f"Mismatch: {orig} vs {rest}"
print("Round-trip OK")