
import pytest
from src.agents.erotic_enhancer import EroticEnhancer
from src.agents.base import BaseAgent
from src.domain.value_objects.erotic_gate import EroticGate

class MockAgent(BaseAgent):
    def __init__(self):
        self.logger = None

@pytest.fixture
def mock_agent():
    return MockAgent()

def test_enhancer_gate_off(mock_agent):
    enhancer = EroticEnhancer(mock_agent)
    context = {
        'erotic_intensity': 2,
        'nsfw_enabled': False,
    }
    result = enhancer.enhance_erotic_content('prompt', 'result', context)
    assert result == 'result'

def test_enhancer_gate_on_intensity0(mock_agent):
    enhancer = EroticEnhancer(mock_agent)
    context = {
        'erotic_intensity': 0,
        'nsfw_enabled': True,
    }
    result = enhancer.enhance_erotic_content('prompt', 'result', context)
    assert result == 'result'

def test_erotic_gate_disabled():
    gate = EroticGate.disabled()
    assert gate.enabled == False
    assert gate.intensity == 0
    assert not gate.is_active()

def test_erotic_gate_from_context_none():
    gate = EroticGate.from_context(None)
    assert gate.enabled == False
    assert gate.intensity == 0
    assert not gate.is_active()

def test_erotic_gate_from_context_empty():
    gate = EroticGate.from_context({})
    assert gate.enabled == False
    assert gate.intensity == 0
    assert not gate.is_active()

def test_erotic_gate_from_context_enable_erotic():
    gate = EroticGate.from_context({'enable_erotic': True})
    assert gate.enabled == True
    assert gate.intensity == 0
    assert not gate.is_active()

def test_erotic_gate_from_context_enable_nsfw():
    gate = EroticGate.from_context({'enable_nsfw': True})
    assert gate.enabled == True
    assert gate.intensity == 0
    assert not gate.is_active()

def test_erotic_gate_from_context_nsfw_enabled():
    gate = EroticGate.from_context({'nsfw_enabled': True})
    assert gate.enabled == True
    assert gate.intensity == 0
    assert not gate.is_active()

def test_erotic_gate_from_context_is_nsfw_enabled():
    gate = EroticGate.from_context({'is_nsfw_enabled': True})
    assert gate.enabled == True
    assert gate.intensity == 0
    assert not gate.is_active()

def test_erotic_gate_from_context_intensity():
    gate = EroticGate.from_context({'erotic_intensity': 3})
    assert gate.enabled == False
    assert gate.intensity == 3
    assert not gate.is_active()

def test_erotic_gate_from_context_both():
    gate = EroticGate.from_context({'enable_erotic': True, 'erotic_intensity': 4})
    assert gate.enabled == True
    assert gate.intensity == 4
    assert gate.is_active()

def test_erotic_gate_from_context_or():
    gate = EroticGate.from_context({
        'enable_erotic': False,
        'enable_nsfw': True,
        'nsfw_enabled': False,
        'is_nsfw_enabled': False
    })
    assert gate.enabled == True

def test_erotic_gate_zero_intensity_inactive():
    gate = EroticGate(enabled=True, intensity=0)
    assert not gate.is_active()

def test_erotic_gate_positive_intensity_active_when_enabled():
    gate = EroticGate(enabled=True, intensity=1)
    assert gate.is_active()
    gate = EroticGate(enabled=False, intensity=1)
    assert not gate.is_active()

