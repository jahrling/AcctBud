from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    version: str
    server_time: str
    timezone: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: dict
    expirationTime: float | None = None


class PushSubscriptionDelete(BaseModel):
    endpoint: str


class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    id: int
    kind: str
    sent_at: datetime
    title: str
    body: str
    result: str

    model_config = {"from_attributes": True}
