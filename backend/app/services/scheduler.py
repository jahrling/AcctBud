import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as pytz_timezone

from app.config import settings
from app.database import SessionLocal
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
        "url": "/acctbud/",
    },
}


def send_scheduled_notification(kind: str) -> None:
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
        send_scheduled_notification,
        CronTrigger(hour=int(evening_h), minute=int(evening_m), timezone=tz),
        args=["evening"],
        id="evening_push",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: morning=%s, evening=%s (%s)",
        settings.morning_time,
        settings.evening_time,
        settings.user_tz,
    )


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
