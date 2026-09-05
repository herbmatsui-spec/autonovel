# tests/unit/test_phase3_fixtures.py
"""Phase 3 フィクスチャ動作確認テスト"""
from __future__ import annotations

import pytest

# Phase 3 フィクスチャを明示的にインポート
pytest_plugins = ["tests.conftest_phase3"]


def test_phase3_config_fixture(phase3_config):
    """Phase3Config フィクスチャが正しく注入される"""
    assert phase3_config is not None
    assert phase3_config.features.compression_enabled is True
    assert phase3_config.features.dag_scheduler_enabled is True
    assert phase3_config.features.social_interaction_enabled is True


def test_mock_llm_fixture(mock_llm):
    """mock_llm フィクスチャが正しく注入される"""
    assert mock_llm is not None
    assert hasattr(mock_llm, 'generate')


def test_mock_graph_client_fixture(mock_graph_client):
    """mock_graph_client フィクスチャが正しく注入される"""
    assert mock_graph_client is not None
    assert hasattr(mock_graph_client, 'query')


def test_mock_redis_fixture(mock_redis):
    """mock_redis フィクスチャが正しく注入される"""
    assert mock_redis is not None
    assert hasattr(mock_redis, 'get')


def test_sample_entities_fixture(sample_entities):
    """sample_entities フィクスチャが正しく注入される"""
    assert isinstance(sample_entities, list)
    assert len(sample_entities) >= 4
    assert sample_entities[0]["name"] == "アレン"
    assert sample_entities[0]["type"] == "character"


def test_sample_relations_fixture(sample_relations):
    """sample_relations フィクスチャが正しく注入される"""
    assert isinstance(sample_relations, list)
    assert len(sample_relations) >= 3
    assert sample_relations[0]["source"] == "e1"
    assert sample_relations[0]["target"] == "e2"


def test_sample_context_fixture(sample_context):
    """sample_context フィクスチャが正しく注入される"""
    assert sample_context["book_id"] == 1
    assert sample_context["branch_id"] == 1
    assert sample_context["ep_num"] == 1


def test_agent_context_fixture(agent_context):
    """agent_context フィクスチャが正しく注入される"""
    from src.agents.orchestrator import AgentContext
    assert isinstance(agent_context, AgentContext)
    assert agent_context.book_id == 1
    assert agent_context.branch_id == 1
    assert agent_context.ep_num == 1