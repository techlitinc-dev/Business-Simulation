"""Per-task model selection.

Override via env vars (``MODEL_EXECUTIVE_SUMMARY``, ``MODEL_COUNTERFACTUAL``,
``MODEL_NARRATIVE``, ``MODEL_DEFAULT``). Falls back to the default
``llm_model`` when no task-specific model is configured.
"""

from __future__ import annotations

from app.core.config import get_settings

#: Report task -> settings field holding the model override.
TASK_MODEL_FIELD_MAP = {
    "executive_summary": "model_executive_summary",
    "counterfactual": "model_counterfactual",
    "financial_narrative": "model_narrative",
    "generic_narrative": "model_narrative",
    "section_default": "model_default",
}


def get_model_for_task(task_name: str) -> str:
    """Return the model for a task: task-specific override > default model."""
    settings = get_settings()
    field = TASK_MODEL_FIELD_MAP.get(task_name, "model_default")
    override = getattr(settings, field, "")
    if override:
        return override
    return settings.llm_model or "deepseek-chat"
