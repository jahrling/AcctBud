from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CheckIn, DailyPlan, DailyPlanItem, Task
from app.services.summary import format_summaries_for_prompt, get_recent_summaries


def today_str(tz_name: str) -> str:
    return datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")


def get_or_create_plan(db: Session, for_date: str) -> DailyPlan:
    existing = db.query(DailyPlan).filter(DailyPlan.for_date == for_date).first()
    if existing:
        return existing

    plan = DailyPlan(for_date=for_date)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_active_tasks(db: Session) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.status == "active")
        .order_by(Task.sort_order, Task.created_at)
        .all()
    )


def build_planning_prompt(
    active_tasks: list[Task],
    yesterday_checkin: CheckIn | None,
    yesterday_reflection_summary: str | None,
    db: Session | None = None,
    for_date: str | None = None,
) -> str:
    lines = [
        "You are AcctBud, a personal accountability companion.",
        "Your role is to help the user plan their day by suggesting 2-3 focus items from their task list.",
        "Guidelines:",
        "- Be concise: 2-3 sentences total.",
        "- Reference specific task names from the data below.",
        "- If yesterday's results are available, acknowledge what was accomplished and gently note what was missed.",
        "- Suggest items that seem high-priority or have been sitting for a while.",
        "- Be warm and encouraging, not prescriptive — the user picks their own plan.",
        "",
    ]

    if yesterday_checkin:
        done = [i for i in yesterday_checkin.items if i.done]
        not_done = [i for i in yesterday_checkin.items if not i.done]
        if done:
            lines.append("Yesterday completed:")
            for item in done:
                lines.append(f"  - [{item.task_category}] {item.task_title}")
        if not_done:
            lines.append("Yesterday not completed:")
            for item in not_done:
                lines.append(f"  - [{item.task_category}] {item.task_title}")
        lines.append("")

    if yesterday_reflection_summary:
        lines.append(f'Yesterday\'s reflection summary: "{yesterday_reflection_summary}"')
        lines.append("")

    lines.append("Today's active tasks:")
    if active_tasks:
        for task in active_tasks:
            line = f"  - [{task.category}] {task.title}"
            if task.note:
                line += f" — {task.note}"
            lines.append(line)
    else:
        lines.append("  (none)")

    if db and for_date:
        summaries = get_recent_summaries(db, for_date)
        summary_block = format_summaries_for_prompt(summaries)
        if summary_block:
            lines.append("")
            lines.append(summary_block)

    lines.extend([
        "",
        "Suggest 2-3 focus items from the task list with brief reasoning.",
        "Do not suggest items that are not in the task list.",
    ])

    return "\n".join(lines)


def get_yesterday_checkin(db: Session, today: str) -> CheckIn | None:
    from datetime import timedelta
    dt = datetime.strptime(today, "%Y-%m-%d")
    yesterday = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    return (
        db.query(CheckIn)
        .filter(CheckIn.for_date == yesterday, CheckIn.status == "completed")
        .first()
    )


def get_yesterday_reflection_summary(db: Session, checkin: CheckIn) -> str | None:
    from app.models import ReflectionMessage

    if not checkin.reflection_finished:
        return None
    messages = (
        db.query(ReflectionMessage)
        .filter(
            ReflectionMessage.check_in_id == checkin.id,
            ReflectionMessage.role != "system",
        )
        .order_by(ReflectionMessage.created_at)
        .all()
    )
    if not messages:
        return None
    last_assistant = [m for m in messages if m.role == "assistant"]
    if last_assistant:
        return last_assistant[-1].content
    return None


def confirm_plan(
    db: Session,
    plan: DailyPlan,
    items: list[dict],
) -> DailyPlan:
    for existing in plan.items:
        db.delete(existing)
    db.flush()

    task_ids = [item["task_id"] for item in items]
    tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
    tasks_by_id = {t.id: t for t in tasks}

    for item in items:
        task = tasks_by_id.get(item["task_id"])
        if not task:
            continue
        plan_item = DailyPlanItem(
            plan_id=plan.id,
            task_id=task.id,
            task_title=task.title,
            task_category=task.category,
            is_key=item.get("is_key", False),
        )
        db.add(plan_item)

    db.flush()
    db.expire(plan, ["items"])

    plan.status = "confirmed"
    plan.confirmed_at = datetime.now(timezone.utc)

    from app.services.journal import write_plan_entry

    plan.journal_written = write_plan_entry(plan)

    db.commit()
    db.refresh(plan)
    return plan
