import asyncio, json, sys
sys.path.append(r'E:\sda')
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.nodes.review_nodes import score_commercial_node

async def run():
    mock_llm = MagicMock()
    # Provide a mock LLM response with varied breakdown values
    mock_llm.generate_json = AsyncMock(return_value=type('Resp', (), {'content': json.dumps({
        'commercial_score': 0.72,
        'is_commercial_ok': True,
        'breakdown': {
            'opening_hook': 0.8,
            'cadence_pull': 0.6,
            'emotional_amplitude': 0.9,
            'mystery_foreshadowing': 0.5,
            'cliffhanger_tension': 0.85
        },
        'advice': ['調整してください']
    }), 'success': True}),
    )
    state = {'ep_num': 1, 'source_content': 'テスト本文'*500}
    res = await score_commercial_node(state, llm_provider=mock_llm)
    print('Result:', res)

asyncio.run(run())
