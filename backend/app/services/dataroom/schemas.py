from datetime import datetime

from pydantic import BaseModel


class DataRoomCreate(BaseModel):
    run_id: str
    expiry_days: int = 7
    label: str = "Investor Data Room"


class DataRoomInfo(BaseModel):
    token: str
    label: str
    run_id: str
    created_at: datetime
    expires_at: datetime
    view_count: int
    download_url: str
    is_active: bool
