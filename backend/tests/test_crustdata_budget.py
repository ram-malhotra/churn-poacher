"""
Tests for Crustdata Application Usage Budget & Safeguards.
Verifies:
- Initial 1,200 credit budget configuration.
- Cumulative usage tracking.
- Status computation: Active / Near Limit / Exhausted.
- Budget exhaustion behavior: blocks new paid requests, prompts for increase.
- User-approved budget increase and audit history recording.
- Separation of demo/mock operations from live usage accounting.
- Account-level safeguards remain strictly enforced.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import AsyncSessionLocal
from app.services.crustdata.credit_guard import CreditGuard
from app.services.crustdata.exceptions import (
    CrustdataBudgetExhaustedError,
    CrustdataCreditDepletedError,
)
from app.services.crustdata.schemas import (
    CrustdataCreditsInfo,
)
from app.models.intelligence import CrustdataBudgetHistory


@pytest.fixture(autouse=True)
def reset_guard_state():
    CreditGuard.reset_in_memory_state(budget=1200.0)
    yield
    CreditGuard.reset_in_memory_state(budget=1200.0)


def test_initial_budget_configuration():
    status = CreditGuard.compute_status(total_budget=1200.0, used_credits=0.0)
    assert status == "Active"
    assert CreditGuard._total_budget == 1200.0
    assert CreditGuard._used_credits == 0.0


def test_status_transitions():
    # 0 / 1200 used (0%) -> Active
    assert CreditGuard.compute_status(1200.0, 0.0) == "Active"

    # 500 / 1200 used (41.6%) -> Active
    assert CreditGuard.compute_status(1200.0, 500.0) == "Active"

    # 959 / 1200 used (79.9%) -> Active
    assert CreditGuard.compute_status(1200.0, 959.0) == "Active"

    # 960 / 1200 used (80.0%) -> Near Limit
    assert CreditGuard.compute_status(1200.0, 960.0) == "Near Limit"

    # 1199 / 1200 used (99.9%) -> Near Limit
    assert CreditGuard.compute_status(1200.0, 1199.0) == "Near Limit"

    # 1200 / 1200 used (100%) -> Exhausted
    assert CreditGuard.compute_status(1200.0, 1200.0) == "Exhausted"

    # 1205 / 1200 used (>100%) -> Exhausted
    assert CreditGuard.compute_status(1200.0, 1205.0) == "Exhausted"


def test_budget_exhaustion_blocks_paid_operations():
    # Simulate usage close to budget
    CreditGuard._used_credits = 1199.0
    CreditGuard._total_budget = 1200.0

    # Operation requiring 2.0 credits should fail (1.0 remaining < 2.0 cost)
    with pytest.raises(CrustdataBudgetExhaustedError) as exc_info:
        CreditGuard.verify_application_budget(estimated_cost=2.0)

    err = exc_info.value
    assert err.budget == 1200.0
    assert err.used == 1199.0
    assert err.remaining == 1.0
    assert err.required_credits == 2.0


def test_account_level_safeguard_remains_active():
    # Application budget has plenty of credits (1200)
    CreditGuard._used_credits = 0.0
    CreditGuard._total_budget = 1200.0

    # But real Crustdata account has only 6 credits left (min threshold is 5)
    account_credits = CrustdataCreditsInfo(
        total_credits=100.0,
        remaining_credits=6.0,
        used_credits=94.0,
    )

    # Level 3 Deep Enrichment requires 15 credits -> 6 - 15 = -9 < 5 min threshold
    # Must be blocked by CrustdataCreditDepletedError, NEVER bypassed by application budget
    with pytest.raises(CrustdataCreditDepletedError):
        CreditGuard.verify_account_balance(estimated_cost=15.0, credits_info=account_credits)


@pytest.mark.asyncio
async def test_mock_usage_isolated_from_live_budget():
    async with AsyncSessionLocal() as db_session:
        await CreditGuard.get_or_create_ledger_db(db_session)
        initial_live_used = CreditGuard._used_credits

        # Record mock usage of 50 credits
        await CreditGuard.record_usage_async(amount=50.0, is_mock=True, db=db_session, notes="Mock test")

        # Live usage must not change
        assert CreditGuard._used_credits == initial_live_used
        # Mock usage must be tracked separately
        assert CreditGuard._mock_used_credits == 50.0


@pytest.mark.asyncio
async def test_budget_increase_with_user_approval():
    async with AsyncSessionLocal() as db_session:
        ledger = await CreditGuard.get_or_create_ledger_db(db_session)
        assert ledger.total_budget == 1200.0

        # User explicitly approves a 500-credit increase
        status = await CreditGuard.increase_budget_async(
            amount=500.0,
            reason="Approved by user for Q4 competitor campaign",
            approved_by="Executive User",
            db=db_session,
        )

        assert status.total_budget == 1700.0
        assert status.remaining_credits == 1700.0
        assert status.status == "Active"

        # Verify history recorded in DB
        history = (await db_session.execute(
            CrustdataBudgetHistory.__table__.select().where(CrustdataBudgetHistory.action == "BUDGET_INCREASE")
        )).fetchall()
        assert len(history) == 1
        assert history[0].amount == 500.0
        assert history[0].approved_by == "Executive User"


@pytest.mark.asyncio
async def test_api_get_budget_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/crustdata/budget")
        assert res.status_code == 200
        data = res.json()
        assert data["total_budget"] >= 1200.0
        assert "used_credits" in data
        assert "remaining_credits" in data
        assert "usage_percentage" in data
        assert data["status"] in ["Active", "Near Limit", "Exhausted"]


@pytest.mark.asyncio
async def test_api_budget_increase_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Increase budget by 300 credits
        payload = {
            "amount": 300.0,
            "reason": "Test budget expansion",
            "approved_by": "QA Auditor",
        }
        res = await ac.post("/api/v1/crustdata/budget/increase", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_budget"] >= 1500.0

        # Verify in history
        hist_res = await ac.get("/api/v1/crustdata/budget/history")
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert any(h["action"] == "BUDGET_INCREASE" and h["amount"] == 300.0 for h in history)


@pytest.mark.asyncio
async def test_api_negative_budget_increase_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/crustdata/budget/increase",
            json={"amount": -50.0, "reason": "Invalid"},
        )
        assert res.status_code in (400, 422)
