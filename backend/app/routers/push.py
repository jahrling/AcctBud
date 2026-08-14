import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import PushSubscription
from app.schemas import PushSubscriptionCreate, PushSubscriptionDelete, PushSubscriptionResponse
from app.services.push import send_to_all

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key")
def vapid_public_key():
    return {"publicKey": settings.vapid_public_key}


@router.post("/subscriptions", response_model=PushSubscriptionResponse)
def create_subscription(sub: PushSubscriptionCreate, db: Session = Depends(get_db)):
    sub_json = json.dumps({"endpoint": sub.endpoint, "keys": sub.keys, "expirationTime": sub.expirationTime})

    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == sub.endpoint).first()
    if existing:
        existing.subscription_json = sub_json
        existing.status = "active"
        db.commit()
        db.refresh(existing)
        return existing

    new_sub = PushSubscription(endpoint=sub.endpoint, subscription_json=sub_json)
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub


@router.delete("/subscriptions")
def delete_subscription(sub: PushSubscriptionDelete, db: Session = Depends(get_db)):
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == sub.endpoint).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Subscription not found")
    existing.status = "expired"
    db.commit()
    return {"status": "ok"}


@router.post("/test")
def test_push(db: Session = Depends(get_db)):
    results = send_to_all(db, title="AcctBud test", body="Push notifications are working!", kind="test")
    return {"results": results, "count": len(results)}
