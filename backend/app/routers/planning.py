import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models import DailyPlan, Task
from app.schemas import (
    PlanConfirmRequest,
    PlanResponse,
    PlanTodayResponse,
    TaskResponse,
)
from app.services.llm import stream_chat
from app.services.planning import (
    build_planning_prompt,
    confirm_plan,
    get_active_tasks,
    get_or_create_plan,
    get_yesterday_checkin,
    get_yesterday_reflection_summary,
    today_str,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("/today", response_model=PlanTodayResponse)
def get_today(db: Session = Depends(get_db)):
    for_date = today_str(settings.user_tz)
    plan = get_or_create_plan(db, for_date)
    active_tasks = get_active_tasks(db)
    return PlanTodayResponse(
        plan=PlanResponse.model_validate(plan),
        active_tasks=[TaskResponse.model_validate(t) for t in active_tasks],
    )


@router.post("/{plan_id}/suggest")
def suggest(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(DailyPlan).filter(DailyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.llm_suggestion:
        return {"suggestion": plan.llm_suggestion, "cached": True}

    active_tasks = get_active_tasks(db)
    yesterday = get_yesterday_checkin(db, plan.for_date)
    reflection_summary = None
    if yesterday:
        reflection_summary = get_yesterday_reflection_summary(db, yesterday)

    system_prompt = build_planning_prompt(
        active_tasks, yesterday, reflection_summary,
        db=db, for_date=plan.for_date,
    )
    messages = [{"role": "system", "content": system_prompt}]

    def generate():
        gen_db = SessionLocal()
        full_response = ""
        try:
            for token in stream_chat(messages):
                full_response += token
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

            gen_plan = gen_db.query(DailyPlan).filter(DailyPlan.id == plan_id).first()
            if gen_plan:
                gen_plan.llm_suggestion = full_response
                gen_db.commit()

            yield f"event: done\ndata: {json.dumps({'suggestion': full_response})}\n\n"
        except GeneratorExit:
            logger.info("Client disconnected during planning suggestion for plan %d", plan_id)
        except Exception:
            logger.exception("Planning suggestion error for plan %d", plan_id)
            yield f"event: error\ndata: {json.dumps({'detail': 'Suggestion unavailable — please try again.'})}\n\n"
        finally:
            gen_db.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{plan_id}/confirm", response_model=PlanResponse)
def confirm(plan_id: int, body: PlanConfirmRequest, db: Session = Depends(get_db)):
    plan = db.query(DailyPlan).filter(DailyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    task_ids = [item.task_id for item in body.items]
    tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
    tasks_by_id = {t.id: t for t in tasks}

    categories_present: set[str] = set()
    work_keys = 0
    personal_keys = 0
    for item in body.items:
        task = tasks_by_id.get(item.task_id)
        if not task:
            raise HTTPException(
                status_code=422, detail=f"Task {item.task_id} not found"
            )
        categories_present.add(task.category)
        if item.is_key:
            if task.category == "work":
                work_keys += 1
            elif task.category == "personal":
                personal_keys += 1

    if "work" in categories_present and work_keys < 1:
        raise HTTPException(
            status_code=422,
            detail="Pick at least 1 key work item",
        )
    if "personal" in categories_present and personal_keys < 1:
        raise HTTPException(
            status_code=422,
            detail="Pick at least 1 key personal item",
        )
    if work_keys + personal_keys < 1:
        raise HTTPException(
            status_code=422,
            detail="Pick at least 1 key item",
        )

    items_dicts = [{"task_id": i.task_id, "is_key": i.is_key} for i in body.items]
    plan = confirm_plan(db, plan, items_dicts)
    return PlanResponse.model_validate(plan)
