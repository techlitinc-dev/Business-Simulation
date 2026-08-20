
from pydantic import BaseModel, Field

REQUIRED_COLUMNS = ["month"]
OPTIONAL_COLUMNS = [
    "revenue", "costs", "cash", "customers", "churn_rate", "cac", "headcount", "mrr",
]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


class ActualsUploadRequest(BaseModel):
    blueprint_id: str
    csv_content: str = Field(..., description="Raw CSV string")
    column_mapping: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Maps CSV column names to blueprint field names. "
            "E.g. {'Monthly Revenue': 'revenue'}"
        ),
    )


class ActualsRowValidation(BaseModel):
    row: int
    errors: list[str]


class ActualsUploadResult(BaseModel):
    records_created: int
    records_updated: int
    validation_warnings: list[ActualsRowValidation]
    unmapped_columns: list[str]
