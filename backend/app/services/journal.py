import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CheckIn

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _render_entry(check_in: CheckIn) -> str:
    completed = check_in.completed_at or datetime.now(timezone.utc)
    utc_str = completed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    done_items = [i for i in check_in.items if i.done]
    not_done_items = [i for i in check_in.items if not i.done]

    lines = [
        "---",
        f"date: {utc_str}",
        "type: checkin",
        f"for_date: {check_in.for_date}",
        f"task_ids: [{', '.join(str(i.task_id) for i in check_in.items)}]",
        "---",
        "",
    ]

    if done_items:
        lines.append("## Done")
        lines.append("")
        for item in done_items:
            lines.append(f"- [{item.task_category}] {item.task_title}")
        lines.append("")

    if not_done_items:
        lines.append("## Not done")
        lines.append("")
        for item in not_done_items:
            lines.append(f"- [{item.task_category}] {item.task_title}")
        lines.append("")

    if not done_items and not not_done_items:
        lines.append("No tasks were active for this check-in.")
        lines.append("")

    if check_in.note:
        lines.append("## Note")
        lines.append("")
        lines.append(check_in.note)
        lines.append("")

    return "\n".join(lines)


def _journal_dir() -> Path | None:
    if not settings.journal_path:
        return None
    return Path(settings.journal_path)


def write_journal_entry(check_in: CheckIn) -> bool:
    journal_dir = _journal_dir()
    if journal_dir is None:
        return False

    if not _DATE_RE.fullmatch(check_in.for_date):
        logger.error("Invalid for_date format: %s", check_in.for_date)
        return False

    year, month, day = check_in.for_date.split("-")
    target_dir = journal_dir / year / month
    target_file = target_dir / f"{day}-checkin.md"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(_render_entry(check_in), encoding="utf-8")
        return True
    except OSError as e:
        logger.warning(
            "Could not write journal entry for %s — Vault may be locked: %s",
            check_in.for_date,
            e,
        )
        return False


def _render_reflection_entry(check_in: CheckIn, messages: list) -> str:
    completed = check_in.completed_at or datetime.now(timezone.utc)
    utc_str = completed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "---",
        f"date: {utc_str}",
        "type: reflection",
        f"for_date: {check_in.for_date}",
        f"check_in_id: {check_in.id}",
        "---",
        "",
        "## Reflection",
        "",
    ]

    for msg in messages:
        if msg.role == "assistant":
            lines.append(f"**AcctBud:** {msg.content}")
            lines.append("")
        elif msg.role == "user":
            lines.append(f"**Me:** {msg.content}")
            lines.append("")

    return "\n".join(lines)


def write_reflection_entry(check_in: CheckIn, messages: list) -> bool:
    journal_dir = _journal_dir()
    if journal_dir is None:
        return False

    if not _DATE_RE.fullmatch(check_in.for_date):
        logger.error("Invalid for_date format: %s", check_in.for_date)
        return False

    year, month, day = check_in.for_date.split("-")
    target_dir = journal_dir / year / month
    target_file = target_dir / f"{day}-reflection.md"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(
            _render_reflection_entry(check_in, messages), encoding="utf-8"
        )
        return True
    except OSError as e:
        logger.warning(
            "Could not write reflection entry for %s — Vault may be locked: %s",
            check_in.for_date,
            e,
        )
        return False


def retry_pending_entries(db: Session) -> int:
    pending = (
        db.query(CheckIn)
        .filter(CheckIn.status == "completed", CheckIn.journal_written.is_(False))
        .all()
    )
    if not pending:
        return 0

    written = 0
    for check_in in pending:
        if write_journal_entry(check_in):
            check_in.journal_written = True
            written += 1

    if written:
        db.commit()
        logger.info("Retried %d pending journal entries, wrote %d", len(pending), written)
    return written


def retry_pending_reflections(db: Session) -> int:
    from app.models import ReflectionMessage

    pending = (
        db.query(CheckIn)
        .filter(
            CheckIn.reflection_finished.is_(True),
            CheckIn.reflection_journal_written.is_(False),
        )
        .all()
    )

    written = 0
    for check_in in pending:
        messages = (
            db.query(ReflectionMessage)
            .filter(
                ReflectionMessage.check_in_id == check_in.id,
                ReflectionMessage.role != "system",
            )
            .order_by(ReflectionMessage.created_at)
            .all()
        )
        if not messages:
            continue
        if write_reflection_entry(check_in, messages):
            check_in.reflection_journal_written = True
            written += 1

    if written:
        db.commit()
        logger.info("Retried %d pending reflection entries", written)
    return written
