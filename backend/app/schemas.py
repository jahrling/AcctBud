from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    category: Literal["work", "personal"]
    note: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    note: str | None = None
    category: Literal["work", "personal"] | None = None
    status: Literal["active", "paused", "archived"] | None = None
    sort_order: float | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    note: str | None
    category: str
    status: str
    sort_order: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    active_count: int


class NotificationLogResponse(BaseModel):
    id: int
    kind: str
    sent_at: datetime
    title: str
    body: str
    result: str

    model_config = {"from_attributes": True}


# Check-ins


class CheckInItemResponse(BaseModel):
    id: int
    task_id: int
    task_title: str
    task_category: str
    done: bool

    model_config = {"from_attributes": True}


class CheckInResponse(BaseModel):
    id: int
    for_date: str
    created_at: datetime
    notified_at: datetime | None
    completed_at: datetime | None
    status: str
    note: str | None
    items: list[CheckInItemResponse]
    reflection_finished: bool
    reflection_journal_written: bool

    model_config = {"from_attributes": True}


class CheckInComplete(BaseModel):
    done_task_ids: list[int] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=500)


class CheckInListResponse(BaseModel):
    checkins: list[CheckInResponse]


# Reflections


class ReflectionMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReflectionResponse(BaseModel):
    messages: list[ReflectionMessageResponse]
    finished: bool


class ReflectionChatRequest(BaseModel):
    message: str | None = Field(default=None, max_length=1000)


class ReflectionFinishResponse(BaseModel):
    journal_written: bool
