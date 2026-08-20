from pydantic import BaseModel


class PortfolioCreate(BaseModel):
    name: str


class WorkspaceSummary(BaseModel):
    workspace_id: str
    label: str
    resilience_score: float | None = None
    survival_rate: float | None = None
    drift_alert: bool = False
    last_run_at: str | None = None


class PortfolioSummary(BaseModel):
    portfolio_id: str
    name: str
    member_count: int
    workspaces: list[WorkspaceSummary]
    avg_resilience_score: float | None = None
