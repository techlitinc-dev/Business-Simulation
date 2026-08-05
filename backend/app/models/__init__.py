"""Model registry.

Every model module added in later phases MUST be imported here so that
Alembic's env.py (which imports this package) picks up its tables via
Base.metadata.
"""

from app.models.blueprint import Blueprint, BlueprintVersion  # noqa: F401
from app.models.simulation import (  # noqa: F401
    Decision,
    RunStatus,
    SimulationEvent,
    SimulationRun,
    TickLog,
)
from app.models.user import User  # noqa: F401
from app.models.workspace import Invite, Membership, Role, Workspace  # noqa: F401
