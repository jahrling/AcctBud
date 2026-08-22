from sqlalchemy.orm import Session

from app.models import CheckIn, ReflectionMessage, Task


def build_system_prompt(check_in: CheckIn, db: Session) -> str:
    done = [i for i in check_in.items if i.done]
    not_done = [i for i in check_in.items if not i.done]

    task_ids = [i.task_id for i in check_in.items]
    tasks_by_id = {}
    if task_ids:
        tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
        tasks_by_id = {t.id: t for t in tasks}

    lines = [
        "You are AcctBud, a personal accountability companion.",
        "Your role is to help the user reflect on their day with warmth and gentle curiosity.",
        "Guidelines:",
        "- Be concise: 2-3 sentences per response.",
        "- Ask one question at a time.",
        "- Use positive reinforcement for what was accomplished.",
        "- If tasks were not completed, be empathetic and curious (not judgmental).",
        "- Never lecture. The user is the author of their own reflection.",
        "- Reference specific task names from the data below.",
        "",
        f"Today's date: {check_in.for_date}",
        "",
    ]

    def _format_item(item):
        line = f"  - [{item.task_category}] {item.task_title}"
        task = tasks_by_id.get(item.task_id)
        if task and task.note:
            line += f" — {task.note}"
        return line

    if done:
        lines.append(f"Completed tasks ({len(done)}):")
        for item in done:
            lines.append(_format_item(item))
    if not_done:
        lines.append(f"Not completed ({len(not_done)}):")
        for item in not_done:
            lines.append(_format_item(item))
    if not done and not not_done:
        lines.append("No tasks were active today.")

    if check_in.note:
        lines.append(f'\nUser\'s note: "{check_in.note}"')

    lines.extend([
        "",
        "Begin by warmly acknowledging what they accomplished (mention tasks by name),",
        "then ask one gentle question to start the reflection.",
        "If nothing was completed, lead with empathy — not every day goes as planned.",
    ])

    return "\n".join(lines)


def get_or_create_system_message(
    db: Session, check_in: CheckIn
) -> ReflectionMessage:
    existing = (
        db.query(ReflectionMessage)
        .filter(
            ReflectionMessage.check_in_id == check_in.id,
            ReflectionMessage.role == "system",
        )
        .first()
    )
    if existing:
        return existing

    msg = ReflectionMessage(
        check_in_id=check_in.id,
        role="system",
        content=build_system_prompt(check_in, db),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_conversation_messages(
    db: Session, check_in_id: int
) -> list[ReflectionMessage]:
    return (
        db.query(ReflectionMessage)
        .filter(ReflectionMessage.check_in_id == check_in_id)
        .order_by(ReflectionMessage.created_at)
        .all()
    )


def save_message(
    db: Session, check_in_id: int, role: str, content: str
) -> ReflectionMessage:
    msg = ReflectionMessage(
        check_in_id=check_in_id,
        role=role,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def messages_to_ollama_format(
    messages: list[ReflectionMessage],
) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in messages]
