from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import DailySummary
from app.schemas import DailySummaryResponse, SummaryListResponse

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.get("", response_model=SummaryListResponse)
def list_summaries(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    summaries = (
        db.query(DailySummary)
        .order_by(DailySummary.for_date.desc())
        .limit(days)
        .all()
    )
    return SummaryListResponse(
        summaries=[DailySummaryResponse.model_validate(s) for s in summaries]
    )
