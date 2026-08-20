"""Model registry.

Every model module added in later phases MUST be imported here so that
Alembic's env.py (which imports this package) picks up its tables via
Base.metadata.
"""

from app.models.actuals import ActualsRecord  # noqa: F401
from app.models.api_key import ApiKey  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.benchmark import BenchmarkSnapshot  # noqa: F401
from app.models.billing import Subscription, UsageRecord  # noqa: F401
from app.models.blueprint import Blueprint, BlueprintVersion  # noqa: F401
from app.models.portfolio import Portfolio, PortfolioMembership  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.scenario import Scenario, ScenarioCategory  # noqa: F401
from app.models.simulation import (  # noqa: F401
    Decision,
    RunStatus,
    SimulationEvent,
    SimulationRun,
    TickLog,
)
from app.models.user import User  # noqa: F401
from app.models.workspace import Invite, Membership, Role, Workspace  # noqa: F401
