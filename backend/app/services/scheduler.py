import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone as pytz_timezone

from app.config import settings
from app.database import SessionLocal
from app.models import CheckIn, Task
from app.services.checkins import get_or_create_checkin, today_str
from app.services.journal import retry_pending_entries, retry_pending_reflections
from app.services.push import send_to_all

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

NOTIFICATION_CONTENT = {
    "morning": {
        "title": "Good morning",
        "body": "Time to plan the day.",
        "url": "/acctbud/",
    },
    "evening": {
        "title": "Evening check-in",
        "body": "How did today go?",
        "url": "/acctbud/checkin/today",
    },
    "followup": {
        "title": "Check-in reminder",
        "body": "Still time to check in tonight.",
        "url": "/acctbud/checkin/today",
    },
}


def send_evening_checkin() -> None:
    db = SessionLocal()
    try:
        active_count = db.query(Task).filter(Task.status == "active").count()
        if active_count == 0:
            logger.info("No active tasks — skipping evening check-in")
            return

        for_date = today_str(settings.user_tz)
        check_in = get_or_create_checkin(db, for_date)

        body = f"{active_count} task{'s' if active_count != 1 else ''} on your list — which ones happened today?"
        results = send_to_all(
            db,
            title=NOTIFICATION_CONTENT["evening"]["title"],
            body=body,
            url=NOTIFICATION_CONTENT["evening"]["url"],
            kind="evening",
        )
        check_in.notified_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Evening check-in push for %s: %s", for_date, results)
    finally:
        db.close()


def send_followup_nag() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=2)

        pending = (
            db.query(CheckIn)
            .filter(
                CheckIn.status == "pending",
                CheckIn.notified_at.is_not(None),
                CheckIn.notified_at <= cutoff,
                CheckIn.followup_at.is_(None),
            )
            .all()
        )

        for check_in in pending:
            content = NOTIFICATION_CONTENT["followup"]
            results = send_to_all(
                db,
                title=content["title"],
                body=content["body"],
                url=content["url"],
                kind="followup",
            )
            check_in.followup_at = now
            db.commit()
            logger.info("Follow-up nag for %s: %s", check_in.for_date, results)
    finally:
        db.close()


def rollover_missed() -> None:
    db = SessionLocal()
    try:
        current_date = today_str(settings.user_tz)
        missed = (
            db.query(CheckIn)
            .filter(
                CheckIn.status == "pending",
                CheckIn.for_date < current_date,
            )
            .all()
        )

        for check_in in missed:
            check_in.status = "missed"
            logger.info("Marked check-in for %s as missed", check_in.for_date)

        if missed:
            db.commit()
    finally:
        db.close()


def retry_journals() -> None:
    db = SessionLocal()
    try:
        retry_pending_entries(db)
        retry_pending_reflections(db)
    finally:
        db.close()


def send_scheduled_notification(kind: str) -> None:
    if kind == "evening":
        send_evening_checkin()
        return

    content = NOTIFICATION_CONTENT.get(kind)
    if not content:
        logger.error("Unknown notification kind: %s", kind)
        return

    db = SessionLocal()
    try:
        results = send_to_all(
            db,
            title=content["title"],
            body=content["body"],
            url=content["url"],
            kind=kind,
        )
        logger.info("Scheduled %s push: %s", kind, results)
    finally:
        db.close()


def start_scheduler() -> None:
    tz = pytz_timezone(settings.user_tz)

    morning_h, morning_m = settings.morning_time.split(":")
    evening_h, evening_m = settings.evening_time.split(":")

    scheduler.add_job(
        send_scheduled_notification,
        CronTrigger(hour=int(morning_h), minute=int(morning_m), timezone=tz),
        args=["morning"],
        id="morning_push",
        replace_existing=True,
    )
    scheduler.add_job(
        send_evening_checkin,
        CronTrigger(hour=int(evening_h), minute=int(evening_m), timezone=tz),
        id="evening_push",
        replace_existing=True,
    )
    scheduler.add_job(
        send_followup_nag,
        IntervalTrigger(minutes=5),
        id="followup_nag",
        replace_existing=True,
    )
    scheduler.add_job(
        rollover_missed,
        CronTrigger(hour=int(morning_h), minute=int(morning_m), timezone=tz),
        id="rollover_missed",
        replace_existing=True,
    )
    scheduler.add_job(
        retry_journals,
        IntervalTrigger(minutes=15),
        id="retry_journals",
        replace_existing=True,
    )

    retry_journals()

    scheduler.start()
    logger.info(
        "Scheduler started: morning=%s, evening=%s (%s)",
        settings.morning_time,
        settings.evening_time,
        settings.user_tz,
    )


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
