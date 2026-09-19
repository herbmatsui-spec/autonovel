import sys
sys.path.insert(0, '.')
from src.agents.planning import PlanningAgent
from unittest.mock import AsyncMock, MagicMock
import asyncio

async def test():
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value={
        'success': True,
        'metadata': {
            'arcs': [
                {'arc_num': 1, 'start_ep': 1, 'end_ep': 10, 'title': '序章', 'summary': 'test'}
            ]
        }
    })
    pm = MagicMock()
    pm.build_arc_generation_prompt.return_value = 'prompt'
    agent = PlanningAgent(llm=llm, prompt_manager=pm)
    
    arcs = await agent.generate_arcs('Test', 'Synopsis', 10, subversion_enabled=True)
    for arc in arcs.arcs:
        print(f'Arc {arc.arc_num}: start={arc.start_ep}, end={arc.end_ep}')
        print(f'  thematic_milestone: {getattr(arc, "thematic_milestone", "NOT SET")}')
        print(f'  has subversion: {hasattr(arc, "subversion")}')
        if hasattr(arc, 'subversion'):
            print(f'  subversion: {arc.subversion}')

asyncio.run(test())