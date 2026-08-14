import json
import logging

from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import NotificationLog, PushSubscription, utcnow

logger = logging.getLogger(__name__)


def send_push(
    db: Session,
    subscription: PushSubscription,
    title: str,
    body: str,
    url: str = "/",
    kind: str = "manual",
) -> str:
    payload = json.dumps({"title": title, "body": body, "url": url})
    sub_info = json.loads(subscription.subscription_json)

    try:
        webpush(
            subscription_info=sub_info,
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        result = "sent"
    except WebPushException as e:
        if e.response and e.response.status_code in (404, 410):
            subscription.status = "expired"
            result = "expired"
        else:
            logger.error("Push failed for subscription %s: %s", subscription.id, e)
            result = "failed"

    log = NotificationLog(
        kind=kind,
        sent_at=utcnow(),
        title=title,
        body=body,
        subscription_id=subscription.id,
        result=result,
    )
    db.add(log)
    db.commit()
    return result


def send_to_all(
    db: Session,
    title: str,
    body: str,
    url: str = "/",
    kind: str = "manual",
) -> list[str]:
    subs = db.query(PushSubscription).filter(PushSubscription.status == "active").all()
    return [send_push(db, sub, title, body, url, kind) for sub in subs]
