"""Unit tests for fusion debug CLI."""
from typer.testing import CliRunner
from unittest.mock import patch

from src.fusion.debug_cli import app
from src.fusion.engine import FusionEngine
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_show_command():
    runner = CliRunner()
    store = InMemoryVectorStore()
    vec = EmotionalVector(episode_id="ep15")
    vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.8, 1.0, "...", "ep15"))
    store.upsert("annotation", "ep15:A->B", vec)

    engine = FusionEngine(store)

    with patch("src.fusion.debug_cli.get_default_engine", return_value=engine):
        result = runner.invoke(app, ["show", "--episode", "15", "--source", "A", "--target", "B", "--json"])
        assert result.exit_code == 0
        assert '"pair": [' in result.output
        assert '"fear"' in result.output
        assert "0.8" in result.output
