"""
Crustdata Credit Guard.
Enforces two-tiered credit protection:
1. Application-Level Spending Budget (Initial: 1,200 credits):
   - Tracks cumulative credits consumed.
   - Status: Active / Near Limit / Exhausted.
   - Blocks new paid API requests when exhausted.
   - Resumes only upon explicit user-approved budget increases.
   - Records every budget change in usage history.
   - Keeps demo/mock operations completely isolated from live usage accounting.
2. Actual Crustdata Account Balance & Billing Thresholds:
   - Verifies real account balance above the safety floor.
   - Never bypasses Crustdata account-level restrictions.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.config import settings
from app.core.logging import logger
from app.services.crustdata.schemas import (
    CrustdataCreditsInfo,
    EnrichmentLevel,
    CrustdataBudgetStatus,
)
from app.services.crustdata.exceptions import (
    CrustdataCreditDepletedError,
    CrustdataBudgetExhaustedError,
)
from app.models.intelligence import CrustdataBudgetLedger, CrustdataBudgetHistory


class CreditGuard:
    """Enforces application budget and account balance safety for Crustdata operations."""

    # In-memory cached state
    _cached_credits: Optional[CrustdataCreditsInfo] = None
    _last_checked_timestamp: float = 0.0
    CACHE_TTL_SECONDS: float = 60.0

    # In-memory fallback budget state (synchronized with DB)
    _total_budget: float = 1200.0
    _used_credits: float = 0.0
    _mock_used_credits: float = 0.0

    # Pricing estimates based on official Crustdata documentation
    OPERATION_COSTS = {
        EnrichmentLevel.LEVEL_1_SEARCH: 0.5,       # Candidate search: ~0.5 - 1 credit
        EnrichmentLevel.LEVEL_2_STANDARD: 2.0,     # Cached database enrichment: ~1 - 2 credits
        EnrichmentLevel.LEVEL_3_DEEP: 15.0,        # Real-time web crawler: ~10 - 25 credits
    }

    @classmethod
    def reset_in_memory_state(cls, budget: float = 1200.0) -> None:
        """Helper for testing to reset in-memory budget state."""
        cls._total_budget = budget
        cls._used_credits = 0.0
        cls._mock_used_credits = 0.0
        cls._cached_credits = None
        cls._last_checked_timestamp = 0.0

    @classmethod
    def estimate_cost(cls, level: EnrichmentLevel) -> float:
        """Returns the estimated credit cost for an enrichment level."""
        return cls.OPERATION_COSTS.get(level, 2.0)

    @classmethod
    def is_cache_valid(cls) -> bool:
        if cls._cached_credits is None:
            return False
        return (time.time() - cls._last_checked_timestamp) < cls.CACHE_TTL_SECONDS

    @classmethod
    def update_cached_credits(cls, credits_info: CrustdataCreditsInfo) -> None:
        cls._cached_credits = credits_info
        cls._last_checked_timestamp = time.time()
        logger.debug(
            f"Crustdata credits updated: remaining={credits_info.remaining_credits:.1f}, "
            f"used={credits_info.used_credits:.1f}"
        )

    @classmethod
    def get_cached_credits(cls) -> Optional[CrustdataCreditsInfo]:
        if cls.is_cache_valid():
            return cls._cached_credits
        return None

    @classmethod
    def compute_status(cls, total_budget: float, used_credits: float) -> str:
        """
        Computes status string:
        - Exhausted: remaining <= 0 or used >= total_budget
        - Near Limit: used >= (CRUSTDATA_NEAR_LIMIT_PERCENT% of budget)
        - Active: otherwise
        """
        remaining = max(0.0, total_budget - used_credits)
        if total_budget <= 0 or used_credits >= total_budget or remaining <= 0:
            return "Exhausted"
        
        near_limit_pct = getattr(settings, "CRUSTDATA_NEAR_LIMIT_PERCENT", 80.0)
        usage_pct = (used_credits / total_budget) * 100.0 if total_budget > 0 else 100.0
        if usage_pct >= near_limit_pct:
            return "Near Limit"
        return "Active"

    @classmethod
    def verify_account_balance(
        cls,
        estimated_cost: float,
        credits_info: Optional[CrustdataCreditsInfo] = None,
    ) -> bool:
        """
        SAFEGUARD: Validates that actual Crustdata account has enough remaining credits above
        the minimum safety floor. Never bypassed by application budget.
        Raises CrustdataCreditDepletedError if account balance is insufficient.
        """
        active_credits = credits_info or cls._cached_credits
        if not active_credits:
            return True

        min_threshold = float(settings.CRUSTDATA_MIN_CREDIT_THRESHOLD)
        remaining = active_credits.remaining_credits

        if remaining - estimated_cost < min_threshold:
            logger.warning(
                f"Credit guard blocked operation: account remaining {remaining:.1f} - cost {estimated_cost:.1f} "
                f"< threshold {min_threshold:.1f}"
            )
            raise CrustdataCreditDepletedError(
                current_balance=remaining,
                required_credits=estimated_cost,
                min_threshold=min_threshold,
            )
        return True

    @classmethod
    def verify_budget_can_proceed(
        cls,
        estimated_cost: float,
        credits_info: Optional[CrustdataCreditsInfo] = None,
    ) -> bool:
        """Backward-compatible alias for verify_account_balance."""
        return cls.verify_account_balance(estimated_cost=estimated_cost, credits_info=credits_info)

    @classmethod
    def verify_application_budget(cls, estimated_cost: float) -> bool:
        """
        Verifies that the application-level spending budget has sufficient remaining credits.
        Raises CrustdataBudgetExhaustedError if budget is exhausted or cannot cover estimated_cost.
        """
        remaining = cls._total_budget - cls._used_credits
        if remaining < estimated_cost or cls._used_credits >= cls._total_budget:
            logger.warning(
                f"Application Crustdata budget exhausted: used {cls._used_credits:.1f}/{cls._total_budget:.1f}, "
                f"remaining {remaining:.1f} < cost {estimated_cost:.1f}"
            )
            raise CrustdataBudgetExhaustedError(
                budget=cls._total_budget,
                used=cls._used_credits,
                remaining=max(0.0, remaining),
                required_credits=estimated_cost,
            )
        return True

    @classmethod
    async def get_or_create_ledger_db(cls, db: AsyncSession) -> CrustdataBudgetLedger:
        """Fetches or initializes the persistent budget ledger record in the database."""
        stmt = select(CrustdataBudgetLedger).where(CrustdataBudgetLedger.id == "global")
        res = await db.execute(stmt)
        ledger = res.scalar_one_or_none()
        if not ledger:
            init_budget = getattr(settings, "CRUSTDATA_INITIAL_BUDGET", 1200.0)
            ledger = CrustdataBudgetLedger(
                id="global",
                total_budget=float(init_budget),
                used_credits=0.0,
                mock_used_credits=0.0,
            )
            db.add(ledger)
            history_init = CrustdataBudgetHistory(
                id=str(uuid.uuid4()),
                action="INITIAL_BUDGET",
                amount=float(init_budget),
                budget_before=0.0,
                budget_after=float(init_budget),
                used_before=0.0,
                used_after=0.0,
                notes=f"Initial application budget established: {init_budget:.0f} credits",
                is_mock=False,
                approved_by="System",
            )
            db.add(history_init)
            await db.commit()
            await db.refresh(ledger)

        # Synchronize in-memory cache
        cls._total_budget = ledger.total_budget
        cls._used_credits = ledger.used_credits
        cls._mock_used_credits = ledger.mock_used_credits
        return ledger

    @classmethod
    async def verify_can_proceed_async(
        cls,
        estimated_cost: float,
        is_mock: bool = False,
        credits_info: Optional[CrustdataCreditsInfo] = None,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Executes both checks:
        1. If not mock: verifies application spending budget (1,200 credits).
        2. Verifies actual Crustdata account balance.
        """
        if db is not None:
            await cls.get_or_create_ledger_db(db)

        if not is_mock:
            cls.verify_application_budget(estimated_cost)

        cls.verify_account_balance(estimated_cost=estimated_cost, credits_info=credits_info)
        return True

    @classmethod
    async def record_usage_async(
        cls,
        amount: float,
        is_mock: bool = False,
        db: Optional[AsyncSession] = None,
        notes: str = "",
    ) -> None:
        """
        Tracks cumulative credits consumed.
        Separates mock operations from live usage accounting.
        """
        if is_mock:
            if db is not None:
                ledger = await cls.get_or_create_ledger_db(db)
                ledger.mock_used_credits += amount
                await db.commit()
                cls._mock_used_credits = ledger.mock_used_credits
            else:
                cls._mock_used_credits += amount
            logger.info(f"Crustdata mock usage recorded: {amount:.1f} credits (Total mock: {cls._mock_used_credits:.1f})")
            return

        # Live usage
        if db is not None:
            ledger = await cls.get_or_create_ledger_db(db)
            prev_used = ledger.used_credits
            ledger.used_credits += amount
            cls._used_credits = ledger.used_credits
            history = CrustdataBudgetHistory(
                id=str(uuid.uuid4()),
                action="USAGE",
                amount=amount,
                budget_before=ledger.total_budget,
                budget_after=ledger.total_budget,
                used_before=prev_used,
                used_after=ledger.used_credits,
                notes=notes or f"Crustdata API operation: {amount:.1f} credits consumed",
                is_mock=False,
                approved_by=None,
            )
            db.add(history)
            await db.commit()
        else:
            cls._used_credits += amount

        logger.info(
            f"Crustdata LIVE usage recorded: +{amount:.1f} credits "
            f"({cls._used_credits:.1f}/{cls._total_budget:.1f} used, "
            f"{cls._total_budget - cls._used_credits:.1f} remaining)"
        )

    @classmethod
    async def increase_budget_async(
        cls,
        amount: float,
        reason: str = "User-approved budget increase",
        approved_by: str = "User",
        db: Optional[AsyncSession] = None,
    ) -> CrustdataBudgetStatus:
        """
        Increases the application-level spending budget upon explicit user approval.
        Records every increase in the usage history.
        """
        if amount <= 0:
            raise ValueError("Budget increase amount must be strictly positive.")

        prev_budget = cls._total_budget

        if db is not None:
            ledger = await cls.get_or_create_ledger_db(db)
            prev_budget = ledger.total_budget
            ledger.total_budget += amount
            history = CrustdataBudgetHistory(
                id=str(uuid.uuid4()),
                action="BUDGET_INCREASE",
                amount=amount,
                budget_before=prev_budget,
                budget_after=ledger.total_budget,
                used_before=ledger.used_credits,
                used_after=ledger.used_credits,
                notes=reason,
                is_mock=False,
                approved_by=approved_by,
            )
            db.add(history)
            await db.commit()
            await db.refresh(ledger)
            cls._total_budget = ledger.total_budget
        else:
            cls._total_budget += amount

        logger.info(
            f"Crustdata budget increased by {amount:.1f} credits: "
            f"new budget {cls._total_budget:.1f} credits (Approved by: {approved_by}, Reason: {reason})"
        )
        return await cls.get_budget_status_async(db=db)

    @classmethod
    async def get_budget_status_async(
        cls,
        db: Optional[AsyncSession] = None,
        credits_info: Optional[CrustdataCreditsInfo] = None,
    ) -> CrustdataBudgetStatus:
        """
        Returns the comprehensive budget status.
        """
        if db is not None:
            await cls.get_or_create_ledger_db(db)

        budget = cls._total_budget
        used = cls._used_credits
        remaining = max(0.0, budget - used)
        usage_pct = (used / budget) * 100.0 if budget > 0 else 100.0
        status = cls.compute_status(budget, used)
        is_exhausted = (status == "Exhausted")

        return CrustdataBudgetStatus(
            total_budget=budget,
            used_credits=used,
            remaining_credits=remaining,
            usage_percentage=round(usage_pct, 2),
            status=status,
            mock_used_credits=cls._mock_used_credits,
            account_credits=credits_info or cls.get_cached_credits(),
            is_exhausted=is_exhausted,
        )
