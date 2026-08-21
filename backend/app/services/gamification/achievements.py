"""Achievement definitions + evaluation against a workspace context dict."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    description: str
    icon: str
    check: Callable[[dict[str, Any]], bool]


ACHIEVEMENTS: list[Achievement] = [
    Achievement(
        id="first_run",
        title="Simulation Pioneer",
        description="Completed your first simulation run",
        icon="🚀",
        check=lambda ctx: ctx.get("total_runs", 0) >= 1,
    ),
    Achievement(
        id="survived_3_shocks",
        title="Shock Absorber",
        description="Survived 3 demand shock hurdles in a single run",
        icon="⚡",
        check=lambda ctx: ctx.get("demand_shocks_survived", 0) >= 3,
    ),
    Achievement(
        id="top_decile",
        title="Top Decile Resilience",
        description="Achieved a resilience score in the top 10% of all simulations",
        icon="🏆",
        check=lambda ctx: ctx.get("cohort_percentile", 0) >= 90,
    ),
    Achievement(
        id="beat_ai_5",
        title="AI Challenger",
        description="Beat the AI's recommended decision path 5 or more times",
        icon="🤖",
        check=lambda ctx: ctx.get("beat_ai_count", 0) >= 5,
    ),
]


def check_achievements(context: dict[str, Any]) -> list[Achievement]:
    """Return every achievement earned for the given workspace context."""
    return [a for a in ACHIEVEMENTS if a.check(context)]
