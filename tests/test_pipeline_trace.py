"""Tests for pipeline /api/pipeline/trace-labels (SCOUT-004 pipeline trace labels)."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestPipelineTraceLabels:
    def test_trace_labels_endpoint_matches_rule_based_path(self, monkeypatch):
        monkeypatch.setenv("USE_LLM", "false")
        response = client.get("/api/pipeline/trace-labels")

        assert response.status_code == 200
        labels = response.json()
        assert labels["use_llm"] is False
        assert labels["composer"] == "RULE-BASED COMPOSER"
        assert labels["wardrobe"] == "WARDROBE SERVICE"
        assert labels["memory"] == "MEMORY SERVICE"
        assert "stylist agent" not in labels["composer"].lower()

    def test_trace_labels_flip_when_llm_enabled(self, monkeypatch):
        monkeypatch.setenv("USE_LLM", "true")
        response = client.get("/api/pipeline/trace-labels")

        labels = response.json()
        assert labels["use_llm"] is True
        assert labels["composer"] == "STYLIST AGENT (LLM)"
