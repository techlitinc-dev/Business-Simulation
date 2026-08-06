"""Idempotent demo seed data (T50).

Run via ``python -m app.utils.seed`` (or ``make seed``). Creates:

- demo user ``demo@forge.dev`` / ``demo-password-123`` (override via
  ``SEED_DEMO_PASSWORD``)
- workspace "Demo Ventures" (owner: demo user)
- 3 Format A blueprints (SaaSFlow, BrewBox, ConsultPro)
- one completed baseline run with tick logs for SaaSFlow (dashboard isn't empty)
- 3 public marketplace scenarios

Idempotent: check-then-insert on email / slug / title.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.blueprint import Blueprint, BlueprintVersion
from app.models.scenario import Scenario
from app.models.simulation import SimulationRun, TickLog
from app.models.user import User
from app.models.workspace import Membership, Role, Workspace

DEMO_EMAIL = "demo@forge.dev"
DEMO_PASSWORD = os.environ.get("SEED_DEMO_PASSWORD", "demo-password-123")
WORKSPACE_NAME = "Demo Ventures"
WORKSPACE_SLUG = "demo-ventures"

_FIXTURES = Path(__file__).resolve().parents[1] / ".." / ".." / "tests" / "fixtures"


def _saasflow_payload() -> dict[str, object]:
    """SaaSFlow — B2B Productivity SaaS ($99/mo, LTV 2400, CAC 850, 5% churn)."""
    return {
        "blueprint_version": "1.0",
        "business_profile": {
            "model_type": "SaaS",
            "stage": "Seed",
            "industry": "B2B Productivity Software",
            "geography": "North America",
        },
        "revenue_engine": {
            "streams": [
                {
                    "name": "Primary Subscription",
                    "pricing_model": "Subscription",
                    "price_point": 99,
                    "projected_customers_month_12": 500,
                    "ltv": 2400,
                    "cac": 850,
                    "churn_monthly": 0.05,
                }
            ]
        },
        "cost_structure": {
            "fixed_monthly": 35000,
            "variable_per_unit": 12,
            "team": [
                {"role": "CEO/Founder", "salary_annual": 80000, "hire_month": 0},
                {"role": "Lead Developer", "salary_annual": 120000, "hire_month": 0},
                {"role": "Sales Rep", "salary_annual": 70000, "hire_month": 3},
            ],
            "burn_rate_month_1": 45000,
        },
        "financials": {
            "starting_capital": 500000,
            "funding_rounds": [],
            "target_runway_months": 18,
        },
        "identified_vulnerabilities": [
            {
                "type": "liquidity",
                "severity": "high",
                "description": (
                    "Burn rate exceeds starting capital runway at current growth."
                ),
                "mitigation_suggestion": (
                    "Reduce fixed costs by 20% or accelerate revenue to Month 4."
                ),
            }
        ],
        "simulation_parameters": {
            "time_step": "monthly",
            "monte_carlo_runs": 100,
            "random_seed": None,
        },
    }


def _brewbox_payload() -> dict[str, object]:
    """BrewBox — DTC Coffee Subscription ($29/mo, higher churn, $120k capital)."""
    return {
        "blueprint_version": "1.0",
        "business_profile": {
            "model_type": "DTC",
            "stage": "Pre-Seed",
            "industry": "DTC Coffee Subscription",
            "geography": "United States",
        },
        "revenue_engine": {
            "streams": [
                {
                    "name": "Coffee Subscription",
                    "pricing_model": "Subscription",
                    "price_point": 29,
                    "projected_customers_month_12": 2500,
                    "ltv": 290,
                    "cac": 80,
                    "churn_monthly": 0.08,
                },
                {
                    "name": "One-off Retail Boxes",
                    "pricing_model": "One-time",
                    "price_point": 45,
                    "projected_customers_month_12": 400,
                    "ltv": 90,
                    "cac": 40,
                    "churn_monthly": 0.0,
                },
            ]
        },
        "cost_structure": {
            "fixed_monthly": 18000,
            "variable_per_unit": 12,
            "team": [
                {"role": "Founder", "salary_annual": 60000, "hire_month": 0},
                {"role": "Roaster", "salary_annual": 55000, "hire_month": 2},
            ],
            "burn_rate_month_1": 23000,
        },
        "financials": {
            "starting_capital": 120000,
            "funding_rounds": [],
            "target_runway_months": 12,
        },
        "identified_vulnerabilities": [
            {
                "type": "market",
                "severity": "medium",
                "description": "High churn (8%) eats into subscription LTV.",
                "mitigation_suggestion": "Invest in retention and loyalty perks.",
            }
        ],
        "simulation_parameters": {
            "time_step": "monthly",
            "monte_carlo_runs": 100,
            "random_seed": None,
        },
    }


def _consultpro_payload() -> dict[str, object]:
    """ConsultPro — Boutique Agency (project pricing, lumpy revenue, $80k)."""
    return {
        "blueprint_version": "1.0",
        "business_profile": {
            "model_type": "Agency",
            "stage": "Seed",
            "industry": "Boutique Consulting",
            "geography": "Global",
        },
        "revenue_engine": {
            "streams": [
                {
                    "name": "Engagement Fees",
                    "pricing_model": "Project",
                    "price_point": 25000,
                    "projected_customers_month_12": 6,
                    "ltv": 60000,
                    "cac": 9000,
                    "churn_monthly": 0.1,
                }
            ]
        },
        "cost_structure": {
            "fixed_monthly": 15000,
            "variable_per_unit": 0,
            "team": [
                {"role": "Principal", "salary_annual": 120000, "hire_month": 0},
                {"role": "Senior Consultant", "salary_annual": 100000, "hire_month": 0},
                {"role": "Analyst", "salary_annual": 60000, "hire_month": 1},
            ],
            "burn_rate_month_1": 26000,
        },
        "financials": {
            "starting_capital": 80000,
            "funding_rounds": [],
            "target_runway_months": 12,
        },
        "identified_vulnerabilities": [
            {
                "type": "operational",
                "severity": "high",
                "description": "Lumpy project revenue with a thin 3-person bench.",
                "mitigation_suggestion": "Diversify into retainers to smooth cash flow.",
            }
        ],
        "simulation_parameters": {
            "time_step": "monthly",
            "monte_carlo_runs": 100,
            "random_seed": None,
        },
    }


def _freemium_assault_payload() -> dict[str, object]:
    """Freemium Assault scenario — embeds a §10 Format B hurdle payload."""
    return {
        "title": "Freemium Assault",
        "description": (
            "A deep-pocketed competitor launches a free tier, forcing pricing "
            "and churn pressure on your core subscription."
        ),
        "category": "competitor_attack",
        "is_public": True,
        "is_featured": True,
        "payload": _saasflow_payload(),
        "hurdle": {
            "event_id": "evt_freemium",
            "trigger_timing": "month 5",
            "category": "market",
            "narrative": {
                "title": "Competitor launches free tier",
                "story": "A rival undercuts pricing with a freemium model.",
                "source_actor": "Competitor X",
                "believability_score": 0.85,
            },
            "mechanical_impact": {
                "immediate": {"cac_delta_percent": 35, "churn_delta_percent": 15},
                "cascading": {"month 9": "churn stays elevated"},
            },
            "ai_game_master_note": "Single-stream concentration exposed.",
        },
    }


def _key_engineer_quits_payload() -> dict[str, object]:
    return {
        "title": "Key Engineer Quits",
        "description": (
            "Your lead engineer walks in month 6 — delivery slows and burn rises "
            "as you backfill."
        ),
        "category": "custom",
        "is_public": True,
        "is_featured": False,
        "payload": _saasflow_payload(),
        "hurdle": {
            "event_id": "evt_engineer",
            "trigger_timing": "month 6",
            "category": "operational",
            "narrative": {
                "title": "Key engineer quits",
                "story": "The lead engineer departs, disrupting the roadmap.",
                "source_actor": "Key hire",
                "believability_score": 0.9,
            },
            "mechanical_impact": {
                "immediate": {"cash_burn_delta_monthly": 8000, "team_morale_delta": -0.2},
                "cascading": {"month 8": "recruiting costs hit"},
            },
            "ai_game_master_note": "Delivery risk is your biggest exposure.",
        },
    }


def _series_a_winter_payload() -> dict[str, object]:
    return {
        "title": "Series A Winter",
        "description": (
            "Investors pull back; a planned round falls through and you must "
            "survive on current capital."
        ),
        "category": "market_crash",
        "is_public": True,
        "is_featured": False,
        "payload": _saasflow_payload(),
        "hurdle": {
            "event_id": "evt_series_a",
            "trigger_timing": "month 9",
            "category": "financial",
            "narrative": {
                "title": "Investor pulls term sheet",
                "story": "A lead investor backs out of the Series A round.",
                "source_actor": "Investor A",
                "believability_score": 0.8,
            },
            "mechanical_impact": {
                "immediate": {"cash_delta_one_time": -75000, "cac_delta_percent": 15},
                "cascading": {"month 12": "funding gap widens"},
            },
            "ai_game_master_note": "Cash is king — extend runway aggressively.",
        },
    }


def _seeded_baseline_result() -> tuple[dict[str, object], list[dict[str, object]]]:
    """A completed baseline run result + a few tick rows (deterministic)."""
    result: dict[str, object] = {
        "survived": True,
        "months_survived": 24,
        "final_cash": 212340.5,
        "final_mrr": 42100.0,
        "peak_cash": 500000.0,
        "min_cash": 88900.0,
        "runway_months": 24.0,
        "resilience_score": 72,
    }
    # A representative 24-month tick series (cash ramps down then recovers).
    ticks: list[dict[str, object]] = []
    cash = 500000.0
    mrr = 0.0
    customers = 0
    for month in range(1, 25):
        if month <= 6:
            growth = 30
        elif month <= 12:
            growth = 45
        elif month <= 18:
            growth = 60
        else:
            growth = 75
        customers += growth
        mrr = customers * 99.0
        cash -= 35000.0
        cash += mrr * 0.8  # ~80% gross margin collected
        burn = 35000.0 - mrr * 0.8
        ticks.append(
            {
                "month": float(month),
                "cash_balance": round(cash, 2),
                "burn_rate": round(burn, 2),
                "runway_months": round(max(cash / max(burn, 1), 0.0), 1),
                "revenue": round(mrr, 2),
                "costs": round(burn + mrr, 2),
                "net_income": round(-burn, 2),
                "mrr": round(mrr, 2),
                "arr": round(mrr * 12, 2),
                "customers": float(customers),
                "churn_rate": 0.05,
                "cac": 850.0,
                "ltv": 1584.0,
                "ltv_cac_ratio": 1.86,
                "new_customers": float(growth),
                "churned_customers": float(round(customers * 0.05)),
            }
        )
    return result, ticks


async def _get_or_create_demo_workspace(db: AsyncSession) -> tuple[User, Workspace]:
    """Idempotently create the demo user + workspace (check-then-insert)."""
    user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            name="Demo User",
            pw_hash=hash_password(DEMO_PASSWORD),
            is_verified=True,
            industry="SaaS",
            stage="Seed",
            primary_fear="Running out of cash before product-market fit",
            onboarding_completed=True,
        )
        db.add(user)
        await db.flush()

    workspace = await db.scalar(
        select(Workspace).where(Workspace.slug == WORKSPACE_SLUG)
    )
    if workspace is None:
        workspace = Workspace(name=WORKSPACE_NAME, slug=WORKSPACE_SLUG, plan_tier="pro")
        db.add(workspace)
        await db.flush()
        db.add(Membership(user_id=user.id, workspace_id=workspace.id, role=Role.OWNER))

    await db.commit()
    return user, workspace


async def _seed_blueprints(
    db: AsyncSession, workspace: Workspace
) -> dict[str, BlueprintVersion]:
    """Create the 3 blueprints; return {name: version} for run/scenario wiring."""
    specs = [
        ("SaaSFlow — B2B Productivity SaaS", "B2B Productivity Software", "Seed",
         _saasflow_payload),
        ("BrewBox — DTC Coffee Subscription", "DTC Coffee Subscription", "Pre-Seed",
         _brewbox_payload),
        ("ConsultPro — Boutique Agency", "Boutique Consulting", "Seed",
         _consultpro_payload),
    ]
    versions: dict[str, BlueprintVersion] = {}
    for name, industry, stage, builder in specs:
        existing = await db.scalar(select(Blueprint).where(Blueprint.name == name))
        if existing is not None:
            version = await db.scalar(
                select(BlueprintVersion).where(
                    BlueprintVersion.blueprint_id == existing.id,
                    BlueprintVersion.version == existing.current_version,
                )
            )
            versions[name] = version  # type: ignore[assignment]
            continue
        bp = Blueprint(workspace_id=workspace.id, name=name, industry=industry, stage=stage)
        db.add(bp)
        await db.flush()
        version = BlueprintVersion(blueprint_id=bp.id, version=1, payload=builder())
        db.add(version)
        await db.flush()
        versions[name] = version
    await db.commit()
    return versions


async def _seed_baseline_run(db: AsyncSession, version: BlueprintVersion) -> None:
    """Seed one completed baseline run for SaaSFlow (idempotent by seed)."""
    existing = await db.scalar(
        select(SimulationRun).where(
            SimulationRun.blueprint_version_id == version.id,
            SimulationRun.mode == "baseline",
            SimulationRun.seed == 42,
        )
    )
    if existing is not None:
        return
    result, ticks = _seeded_baseline_result()
    workspace_id = await _workspace_id_for(db, version)
    run = SimulationRun(
        workspace_id=workspace_id,
        blueprint_version_id=version.id,
        mode="baseline",
        status="completed",
        seed=42,
        current_month=24,
        config={"months": 24},
        result=result,
        started_at=None,
        finished_at=None,
    )
    db.add(run)
    await db.flush()
    for tick in ticks:
        db.add(
            TickLog(
                run_id=run.id,
                month=int(tick["month"]),  # type: ignore[call-overload]
                kpis=tick,
            )
        )
    await db.commit()


async def _workspace_id_for(
    db: AsyncSession, version: BlueprintVersion
) -> str:
    bp = await db.get(Blueprint, version.blueprint_id)
    if bp is None:  # pragma: no cover - version was just created above
        raise RuntimeError(f"blueprint {version.blueprint_id} not found")
    return bp.workspace_id


async def _seed_scenarios(
    db: AsyncSession, workspace: Workspace
) -> None:
    """Create 3 public scenarios authored by the demo workspace (idempotent)."""
    from app.schemas.blueprint import BlueprintPayload

    specs = [
        _freemium_assault_payload(),
        _key_engineer_quits_payload(),
        _series_a_winter_payload(),
    ]
    for spec in specs:
        existing = await db.scalar(
            select(Scenario).where(Scenario.title == str(spec["title"]))
        )
        if existing is not None:
            continue
        payload = dict(spec["payload"])  # type: ignore[call-overload]
        # Validate the payload parses as Format A before storing.
        BlueprintPayload.model_validate(payload)
        scenario = Scenario(
            author_workspace_id=workspace.id,
            title=spec["title"],
            description=spec["description"],
            category=spec["category"],
            payload=payload,
            is_public=spec["is_public"],
            is_featured=spec["is_featured"],
        )
        db.add(scenario)
    await db.commit()


async def seed(session: AsyncSession) -> None:
    """Idempotently seed demo content into the given session."""
    from app.schemas.blueprint import BlueprintPayload

    user, workspace = await _get_or_create_demo_workspace(session)
    versions = await _seed_blueprints(session, workspace)

    # Validate every seeded payload against Format A.
    for version in versions.values():
        BlueprintPayload.model_validate(dict(version.payload))

    saasflow = versions["SaaSFlow — B2B Productivity SaaS"]
    await _seed_baseline_run(session, saasflow)
    await _seed_scenarios(session, workspace)
    await session.commit()


if __name__ == "__main__":
    import asyncio

    from app.db.base import Base
    from app.db.session import async_engine, async_session_factory

    async def _main() -> None:
        # Create tables if the DB is fresh (normally alembic has run already).
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_session_factory() as session:
            await seed(session)
            print(f"Seeded demo user {DEMO_EMAIL} / {DEMO_PASSWORD}")

    asyncio.run(_main())
