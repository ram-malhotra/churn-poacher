"""
Tests for Natural Language Objective Interpreter and API.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.objective.objective_interpreter import ObjectiveInterpreter, ObjectiveCriteria


def test_interpret_complex_enterprise_objective():
    prompt = (
        "Find companies in the US and India experiencing high Datadog observability costs, "
        "unexpected billing increases, performance issues, or outages. Prioritize companies "
        "discussing migration to OpenTelemetry, Grafana, or SigNoz. Focus on companies with 200–5000 employees."
    )
    criteria = ObjectiveInterpreter.interpret(prompt)

    # 1. Geographies
    assert "US" in criteria.target_geography
    assert "India" in criteria.target_geography
    assert len(criteria.target_geography) == 2

    # 2. Company Size
    assert criteria.target_company_size is not None
    assert criteria.target_company_size.min == 200
    assert criteria.target_company_size.max == 5000

    # 3. Target Vendor
    assert criteria.target_vendor == "Datadog"

    # 4. Industry should be None (not specified)
    assert criteria.target_industry is None

    # 5. Pain Points
    assert "HIGH_OBSERVABILITY_COSTS" in criteria.pain_points
    assert "UNEXPECTED_BILLING_INCREASES" in criteria.pain_points
    assert "OUTAGES_AND_DOWNTIME" in criteria.pain_points
    assert "PERFORMANCE_AND_OVERHEAD" in criteria.pain_points

    # 6. Migration Intent & Challengers
    assert criteria.migration_intent is True
    assert "OpenTelemetry" in criteria.alternative_technologies
    assert "Grafana" in criteria.alternative_technologies
    assert "SigNoz" in criteria.alternative_technologies

    # 7. Tailored Search Queries
    assert "datadog pricing" in criteria.search_queries
    assert "datadog opentelemetry" in criteria.search_queries
    assert "datadog grafana" in criteria.search_queries
    assert "datadog signoz" in criteria.search_queries
    assert "datadog outage" in criteria.search_queries


def test_interpret_minimal_pricing_and_migration_objective():
    prompt = "Find companies discussing Datadog pricing concerns or migration to OpenTelemetry."
    criteria = ObjectiveInterpreter.interpret(prompt)

    assert criteria.target_vendor == "Datadog"
    assert criteria.target_geography == []
    assert criteria.target_company_size is None
    assert criteria.target_industry is None
    assert "HIGH_OBSERVABILITY_COSTS" in criteria.pain_points
    assert criteria.migration_intent is True
    assert "OpenTelemetry" in criteria.alternative_technologies
    assert "datadog pricing" in criteria.search_queries
    assert "datadog opentelemetry" in criteria.search_queries


def test_no_silent_invention_of_criteria():
    prompt = "Show me teams unhappy with Datadog."
    criteria = ObjectiveInterpreter.interpret(prompt)

    assert criteria.target_vendor == "Datadog"
    assert criteria.target_geography == []
    assert criteria.target_company_size is None
    assert criteria.target_industry is None
    assert criteria.alternative_technologies == []


@pytest.mark.asyncio
async def test_api_interpret_objective_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/orchestrator/interpret-objective",
            json={"objective": "Find SaaS companies in Germany switching from Datadog to Grafana."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_vendor"] == "Datadog"
        assert "Germany" in data["target_geography"]
        assert data["target_industry"] == "SaaS"
        assert data["migration_intent"] is True
        assert "Grafana" in data["alternative_technologies"]
