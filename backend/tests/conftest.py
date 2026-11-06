"""
Pytest configuration and global fixtures for backend test suite.
"""

import pytest
from sqlalchemy import text
from app.db.session import async_engine, init_db


@pytest.fixture(autouse=True)
def hermetic_crustdata_for_unit_tests(monkeypatch):
    """Ensures unit test suite is hermetic, offline, and does not depend on live credit balance."""
    from app.core.config import settings
    from app.services.crustdata.credit_guard import CreditGuard
    monkeypatch.setattr(settings, "CRUSTDATA_API_KEY", None)
    CreditGuard._cached_credits = None


@pytest.fixture(autouse=True)
async def clean_database():
    """Initializes tables and truncates/cleans all records before each test runs."""
    await init_db()
    async with async_engine.begin() as conn:
        # Disable foreign keys temporarily to truncate tables cleanly in SQLite
        if "sqlite" in str(async_engine.url):
            await conn.execute(text("PRAGMA foreign_keys = OFF;"))
            await conn.execute(text("DELETE FROM deposition_dossiers;"))
            await conn.execute(text("DELETE FROM workflow_executions;"))
            await conn.execute(text("DELETE FROM companies;"))
            await conn.execute(text("DELETE FROM signals;"))
            await conn.execute(text("DELETE FROM agent_execution_logs;"))
            await conn.execute(text("DELETE FROM intelligence_evidence;"))
            await conn.execute(text("DELETE FROM intelligence_searches;"))
            await conn.execute(text("DELETE FROM intelligence_entities;"))
            await conn.execute(text("DELETE FROM crustdata_budget_history;"))
            await conn.execute(text("DELETE FROM crustdata_budget_ledgers;"))
            await conn.execute(text("DELETE FROM campaigns;"))
            await conn.execute(text("PRAGMA foreign_keys = ON;"))
        else:
            await conn.execute(text("TRUNCATE TABLE workflow_executions, deposition_dossiers, companies, signals, agent_execution_logs, intelligence_evidence, intelligence_searches, intelligence_entities, crustdata_budget_history, crustdata_budget_ledgers, campaigns CASCADE;"))
    yield
