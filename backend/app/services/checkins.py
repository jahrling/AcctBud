from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import CheckIn, CheckInItem, Task


def today_str(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")


def get_or_create_checkin(db: Session, for_date: str) -> CheckIn:
    existing = db.query(CheckIn).filter(CheckIn.for_date == for_date).first()
    if existing:
        return existing

    active_tasks = (
        db.query(Task)
        .filter(Task.status == "active")
        .order_by(Task.sort_order, Task.created_at)
        .all()
    )

    check_in = CheckIn(for_date=for_date)
    db.add(check_in)
    db.flush()

    for task in active_tasks:
        item = CheckInItem(
            check_in_id=check_in.id,
            task_id=task.id,
            task_title=task.title,
            task_category=task.category,
        )
        db.add(item)

    db.commit()
    db.refresh(check_in)
    return check_in


def complete_checkin(
    db: Session,
    check_in: CheckIn,
    done_task_ids: list[int],
    note: str | None,
) -> CheckIn:
    done_set = set(done_task_ids)
    for item in check_in.items:
        item.done = item.task_id in done_set
    check_in.note = note
    check_in.completed_at = datetime.now(timezone.utc)
    check_in.status = "completed"

    from app.services.journal import write_journal_entry

    check_in.journal_written = write_journal_entry(check_in)

    db.commit()
    db.refresh(check_in)
    return check_in
