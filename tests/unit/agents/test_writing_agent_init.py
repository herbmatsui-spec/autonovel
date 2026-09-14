import pytest
from src.agents.writing.writing import WritingAgent

def test_writing_agent_initialization():
    agent = WritingAgent(model_name="test-model", temperature=0.7)
    assert agent.model_name == "test-model"
    assert agent.temperature == 0.7