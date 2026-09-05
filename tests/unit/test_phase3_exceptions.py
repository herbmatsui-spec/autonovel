"""Unit tests for Phase 3 exception error code format (Step 22)."""
import pytest
from src.core.exceptions.phase3 import (
    CompressionError,
    DAGSchedulerError,
    SocialInteractionError,
    ConfigurationError,
    ResourceExhaustedError,
)


def test_compression_error_default_code():
    """CompressionError のデフォルト引数で error_code == "PHASE3_COMPRESSION_001" となることの検証."""
    err = CompressionError("test message")
    assert err.error_code == "PHASE3_COMPRESSION_001"


def test_compression_error_with_prefix():
    """CompressionError に PREFIX 付きコード渡しても二重にならないことの検証."""
    err = CompressionError("test", error_code="PHASE3_COMPRESSION_001")
    assert err.error_code == "PHASE3_COMPRESSION_001"


def test_compression_error_without_prefix():
    """CompressionError に PREFIX なしコード渡しても正しく付与されることの検証."""
    err = CompressionError("test", error_code="002")
    assert err.error_code == "PHASE3_COMPRESSION_002"


def test_dag_scheduler_error_default_code():
    """DAGSchedulerError のデフォルト引数で error_code == "PHASE3_DAG_001" となることの検証."""
    err = DAGSchedulerError("test message")
    assert err.error_code == "PHASE3_DAG_001"


def test_dag_scheduler_error_double_prefix_protection():
    """DAGSchedulerError に PREFIX 付きコード渡しても二重にならないことの検証."""
    err = DAGSchedulerError("test", error_code="PHASE3_DAG_003")
    assert err.error_code == "PHASE3_DAG_003"


def test_social_interaction_error_default_code():
    """SocialInteractionError のデフォルト引数で error_code == "PHASE3_SOCIAL_001" となることの検証."""
    err = SocialInteractionError("test message")
    assert err.error_code == "PHASE3_SOCIAL_001"


def test_configuration_error_default_code():
    """ConfigurationError のデフォルト引数で error_code == "PHASE3_CONFIG_001" となることの検証."""
    err = ConfigurationError("test message")
    assert err.error_code == "PHASE3_CONFIG_001"


def test_resource_exhausted_error_default_code():
    """ResourceExhaustedError のデフォルト引数で error_code == "PHASE3_RESOURCE_001" となることの検証."""
    err = ResourceExhaustedError("test message")
    assert err.error_code == "PHASE3_RESOURCE_001"
