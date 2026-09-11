"""AuditorModelRouter unit tests (Step 46)"""

import pytest
from src.agents.specialists.model_router import AuditorModelRouter


class TestAuditorModelRouter:
    def test_config_loaded(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        assert len(router._auditor_model_mapping) == 8
        assert "factual" in router._auditor_model_mapping
        assert "creativity" in router._auditor_model_mapping
        assert "structure" in router._auditor_model_mapping

    def test_lightweight_auditors_use_gemini(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        assert router.get_provider_for_auditor("factual") == "gemini"
        assert router.get_provider_for_auditor("consistency") == "gemini"
        assert router.get_provider_for_auditor("style") == "gemini"
        assert router.get_provider_for_auditor("multimodal") == "gemini"

    def test_heavy_auditors_use_sonnet_or_gpt4o(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        assert router.get_provider_for_auditor("creativity") == "claude"
        assert router.get_provider_for_auditor("emotion_curve") == "claude"
        assert router.get_provider_for_auditor("structure") == "openai"
        assert router.get_provider_for_auditor("reader_hook") == "openai"

    def test_list_configured_auditors(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        auditors = router.list_configured_auditors()
        assert len(auditors) == 8
        assert set(auditors) == {
            "factual", "consistency", "style", "multimodal",
            "creativity", "reader_hook", "emotion_curve", "structure"
        }

    def test_fallback_chains_present(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        # Each provider should have a fallback chain (may be empty)
        for provider in ["gemini", "claude", "openai"]:
            chain = router.fallback_chains.get(provider, [])
            assert isinstance(chain, list)
            # Note: fallback chains don't include the provider itself
            # they only contain alternative providers

    def test_hot_reload(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        # Initial mapping
        assert router._auditor_model_mapping["factual"] == "google/gemini-1.5-flash"
        # Refresh should not break
        router.refresh_from_config("config/audit_models.yaml")
        assert "factual" in router._auditor_model_mapping

    def test_get_llm_for_auditor_returns_none_without_clients(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        # No clients registered, should return None
        assert router.get_llm_for_auditor("factual") is None

    def test_register_client_and_retrieve(self):
        router = AuditorModelRouter("config/audit_models.yaml")
        mock_client = object()
        router.register_client("gemini", mock_client)
        # factual uses gemini provider
        result = router.get_llm_for_auditor("factual")
        assert result is mock_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])