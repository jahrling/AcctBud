import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    CheckIn,
    CheckInItem,
    DailyPlan,
    DailyPlanItem,
    DailySummary,
    ReflectionMessage,
)
from app.services.llm import complete

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "You are a concise summarizer. Given a person's daily accountability data "
    "(plan, check-in results, reflection conversation), write a single paragraph "
    "of 2-4 sentences capturing: what they planned, what they accomplished, what "
    "they didn't, and any notable insight from their reflection. Use third person "
    "('they'). Do not add advice or encouragement — just the facts and any self-"
    "reported reason for what happened. Keep it under 150 tokens."
)


def gather_day_data(db: Session, for_date: str) -> str | None:
    """Pull all structured data for a date and return a text block, or None if
    there's nothing meaningful to summarize (no completed check-in)."""
    check_in = (
        db.query(CheckIn)
        .filter(CheckIn.for_date == for_date, CheckIn.status == "completed")
        .first()
    )
    if not check_in:
        return None

    lines: list[str] = [f"Date: {for_date}", ""]

    plan = db.query(DailyPlan).filter(DailyPlan.for_date == for_date).first()
    if plan and plan.status == "confirmed":
        plan_items = (
            db.query(DailyPlanItem).filter(DailyPlanItem.plan_id == plan.id).all()
        )
        if plan_items:
            lines.append("Morning plan:")
            for item in plan_items:
                key = " (key focus)" if item.is_key else ""
                lines.append(f"  - [{item.task_category}] {item.task_title}{key}")
            lines.append("")

    done = [i for i in check_in.items if i.done]
    not_done = [i for i in check_in.items if not i.done]

    if done:
        lines.append("Completed:")
        for item in done:
            lines.append(f"  - [{item.task_category}] {item.task_title}")
    if not_done:
        lines.append("Not completed:")
        for item in not_done:
            lines.append(f"  - [{item.task_category}] {item.task_title}")
    lines.append("")

    if check_in.note:
        lines.append(f'Check-in note: "{check_in.note}"')
        lines.append("")

    reflection_msgs = (
        db.query(ReflectionMessage)
        .filter(
            ReflectionMessage.check_in_id == check_in.id,
            ReflectionMessage.role != "system",
        )
        .order_by(ReflectionMessage.created_at)
        .all()
    )
    if reflection_msgs:
        lines.append("Reflection conversation:")
        for msg in reflection_msgs:
            speaker = "AcctBud" if msg.role == "assistant" else "User"
            lines.append(f"  {speaker}: {msg.content}")
        lines.append("")

    return "\n".join(lines)


def generate_summary(db: Session, for_date: str) -> DailySummary | None:
    """Generate and store a daily summary for the given date. Returns the
    summary, or None if the day has no data or a summary already exists."""
    existing = (
        db.query(DailySummary).filter(DailySummary.for_date == for_date).first()
    )
    if existing:
        return existing

    day_data = gather_day_data(db, for_date)
    if not day_data:
        return None

    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": day_data},
    ]

    try:
        summary_text = complete(messages, max_tokens=200, temperature=0.3)
    except Exception:
        logger.exception("Failed to generate summary for %s", for_date)
        return None

    if not summary_text:
        logger.warning("Empty summary returned for %s", for_date)
        return None

    summary = DailySummary(
        for_date=for_date,
        summary_text=summary_text,
        generated_at=datetime.now(timezone.utc),
        model_used=settings.ollama_model,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    logger.info("Generated daily summary for %s (%d chars)", for_date, len(summary_text))
    return summary


def get_recent_summaries(db: Session, before_date: str, n: int = 7) -> list[DailySummary]:
    """Return the last N summaries strictly before the given date, newest first."""
    return (
        db.query(DailySummary)
        .filter(DailySummary.for_date < before_date)
        .order_by(DailySummary.for_date.desc())
        .limit(n)
        .all()
    )


def format_summaries_for_prompt(summaries: list[DailySummary]) -> str:
    """Format summaries (newest-first) into a prompt section. Returns empty
    string if no summaries are available."""
    if not summaries:
        return ""
    lines = ["Recent days:"]
    for s in reversed(summaries):
        lines.append(f"  {s.for_date}: {s.summary_text}")
    return "\n".join(lines)


def backfill_summaries(db: Session) -> int:
    """Generate summaries for past dates that have completed check-ins but
    no summary yet. Returns the count of summaries generated."""
    completed_dates = (
        db.query(CheckIn.for_date)
        .filter(CheckIn.status == "completed")
        .all()
    )
    existing_dates = set(
        row[0] for row in db.query(DailySummary.for_date).all()
    )

    generated = 0
    for (for_date,) in completed_dates:
        if for_date in existing_dates:
            continue
        result = generate_summary(db, for_date)
        if result:
            generated += 1

    if generated:
        logger.info("Backfilled %d daily summaries", generated)
    return generated
