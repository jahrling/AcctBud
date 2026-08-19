from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import CheckIn
from app.schemas import CheckInComplete, CheckInListResponse, CheckInResponse
from app.services.checkins import complete_checkin, get_or_create_checkin, today_str

router = APIRouter(prefix="/api/checkins", tags=["checkins"])


@router.get("/today", response_model=CheckInResponse)
def get_today(db: Session = Depends(get_db)):
    for_date = today_str(settings.user_tz)
    check_in = get_or_create_checkin(db, for_date)
    return check_in


@router.post("/{checkin_id}/complete", response_model=CheckInResponse)
def complete(checkin_id: int, body: CheckInComplete, db: Session = Depends(get_db)):
    check_in = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
    if not check_in:
        raise HTTPException(status_code=404, detail="Check-in not found")
    if check_in.status == "missed":
        raise HTTPException(status_code=409, detail="Cannot complete a missed check-in")
    return complete_checkin(db, check_in, body.done_task_ids, body.note)


@router.get("", response_model=CheckInListResponse)
def list_checkins(limit: int = Query(default=30, ge=1, le=100), db: Session = Depends(get_db)):
    checkins = (
        db.query(CheckIn)
        .order_by(CheckIn.for_date.desc())
        .limit(limit)
        .all()
    )
    return CheckInListResponse(checkins=checkins)
