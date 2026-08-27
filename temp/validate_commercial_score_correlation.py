import asyncio, json, sys, math
from typing import List, Tuple

# Ensure project root in path
sys.path.append(r'E:\\sda')

from src.backend.workflows.nodes.review_nodes import score_commercial_node

# Mock LLM provider that returns scores based on a pre‑defined mapping per episode id
class MockLLM:
    def __init__(self, scores_map):
        self.scores_map = scores_map
    async def generate_json(self, model_name: str, prompt: str, temperature: float = 0.2):
        # Determine a simple deterministic score based on keywords present in the prompt content
        if 'Hookstrong' in prompt:
            return type('Resp', (), {'content': json.dumps(self.scores_map['A']), 'success': True})
        if 'Hookmid' in prompt:
            return type('Resp', (), {'content': json.dumps(self.scores_map['B']), 'success': True})
        if 'Hookweak' in prompt:
            return type('Resp', (), {'content': json.dumps(self.scores_map['C']), 'success': True})
        # Fallback default
        return type('Resp', (), {'content': json.dumps({"commercial_score": 0.5, "breakdown": {}, "advice": []}), 'success': True})

# Synthetic episode data – content includes a hidden marker for the mock provider
episodes = [
    {"ep_num": 1, "source_content": "__ID:A__ Hookstrong middlepull highemotion mysthigh cliffhigh"},
    {"ep_num": 2, "source_content": "__ID:B__ Hookmid middlepull lowemotion mystmid cliffmid"},
    {"ep_num": 3, "source_content": "__ID:C__ Hookweak lowpull lowemotion mystlow clifflow"},
]

# Pre‑defined scores that reflect the intuitive quality of each episode
scores_map = {
    "A": {"commercial_score": 0.92,
          "breakdown": {"opening_hook": 0.95, "cadence_pull": 0.9,
                         "emotional_amplitude": 0.94, "mystery_foreshadowing": 0.9,
                         "cliffhanger_tension": 0.93},
          "advice": []},
    "B": {"commercial_score": 0.68,
          "breakdown": {"opening_hook": 0.65, "cadence_pull": 0.7,
                         "emotional_amplitude": 0.6, "mystery_foreshadowing": 0.7,
                         "cliffhanger_tension": 0.65},
          "advice": []},
    "C": {"commercial_score": 0.42,
          "breakdown": {"opening_hook": 0.4, "cadence_pull": 0.45,
                         "emotional_amplitude": 0.3, "mystery_foreshadowing": 0.35,
                         "cliffhanger_tension": 0.4},
          "advice": []},
}

mock_llm = MockLLM(scores_map)

async def run():
    results: List[Tuple[str, float]] = []
    for ep in episodes:
        res = await score_commercial_node(ep, llm_provider=mock_llm)
        # Extract marker id from source_content for reporting
        ep_id = ep["source_content"].split('__ID:')[1][0]
        results.append((ep_id, res["commercial_score"]))
    return results

scores = asyncio.run(run())
print('Episode scores:', scores)

# Simple correlation against a manual ranking (A=3, B=2, C=1)
manual = {'A': 3, 'B': 2, 'C': 1}
xs = [manual[e] for e, _ in scores]
ys = [s for _, s in scores]
# Pearson correlation
n = len(xs)
mean_x = sum(xs)/n
mean_y = sum(ys)/n
cov = sum((x-mean_x)*(y-mean_y) for x, y in zip(xs, ys))
var_x = sum((x-mean_x)**2 for x in xs)
var_y = sum((y-mean_y)**2 for y in ys)
pearson = cov / math.sqrt(var_x*var_y) if var_x and var_y else 0
print('Pearson correlation (manual ranking <-> commercial_score):', round(pearson, 3))
