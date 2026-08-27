import sys, json, asyncio
sys.path.append(r'E:\\sda')
from src.backend.kakuyomu.commercial_validation import compute_correlation

class MockLLM:
    def __init__(self, score_map):
        self.score_map = score_map
    async def generate_json(self, model_name, prompt, temperature=0.2):
        marker = next((line for line in prompt.split('\n') if line.startswith('__ID:')), None)
        if marker:
            ep_id = marker.split(':',1)[1].strip()
            data = self.score_map.get(ep_id, {'commercial_score':0.5,'breakdown':{},'advice':[]})
        else:
            data = {'commercial_score':0.5,'breakdown':{},'advice':[]}
        return type('Resp',(),{'content': json.dumps(data), 'success': True})

works = [
    {'work_id':'1','bookmark':300,'excerpt':'__ID:A__'},
    {'work_id':'2','bookmark':200,'excerpt':'__ID:B__'},
    {'work_id':'3','bookmark':100,'excerpt':'__ID:C__'},
]
score_map = {
    'A':{'commercial_score':0.9,'breakdown':{},'advice':[]},
    'B':{'commercial_score':0.6,'breakdown':{},'advice':[]},
    'C':{'commercial_score':0.3,'breakdown':{},'advice':[]},
}
mock_llm = MockLLM(score_map)

# Compute each work individually for debugging
import pprint

async def compute_individuals():
    results = []
    from src.backend.kakuyomu.commercial_validation import compute_correlation
    for w in works:
        state = {"ep_num": w["work_id"], "source_content": w["excerpt"]}
        res = await compute_correlation([w], llm_provider=mock_llm)  # careful: compute_correlation expects list, but we want node directly.
    
# Instead, call the node directly
from src.backend.workflows.nodes.review_nodes import score_commercial_node

async def run_debug():
    for w in works:
        state = {"ep_num": w["work_id"], "source_content": w["excerpt"]}
        result = await score_commercial_node(state, llm_provider=mock_llm)
        print('Work', w["work_id"], 'result', result)
    # Finally compute correlation using original function
    corr = asyncio.run(compute_correlation(works, llm_provider=mock_llm))
    print('corr:', corr)

asyncio.run(run_debug())

