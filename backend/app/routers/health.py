from datetime import datetime, timezone

from fastapi import APIRouter
from pytz import timezone as pytz_timezone

from app.config import settings
from app.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health():
    tz = pytz_timezone(settings.user_tz)
    now = datetime.now(timezone.utc).astimezone(tz)
    return HealthResponse(
        version="0.1.0",
        server_time=now.isoformat(),
        timezone=settings.user_tz,
    )
