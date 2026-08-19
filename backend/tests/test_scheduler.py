from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.scheduler import send_scheduled_notification, NOTIFICATION_CONTENT


@patch("app.services.scheduler.send_to_all")
@patch("app.services.scheduler.SessionLocal")
def test_send_scheduled_notification_morning(mock_session_cls, mock_send_to_all):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    mock_send_to_all.return_value = ["sent"]

    send_scheduled_notification("morning")

    mock_send_to_all.assert_called_once_with(
        mock_db,
        title="Good morning",
        body="Time to plan the day.",
        url="/acctbud/",
        kind="morning",
    )
    mock_db.close.assert_called_once()


@patch("app.services.scheduler.send_to_all")
@patch("app.services.scheduler.SessionLocal")
def test_send_scheduled_notification_evening(mock_session_cls, mock_send_to_all):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    mock_send_to_all.return_value = ["sent"]

    send_scheduled_notification("evening")

    mock_send_to_all.assert_called_once_with(
        mock_db,
        title="Evening check-in",
        body="How did today go?",
        url="/acctbud/",
        kind="evening",
    )


@patch("app.services.scheduler.send_to_all")
@patch("app.services.scheduler.SessionLocal")
def test_send_scheduled_unknown_kind_does_nothing(mock_session_cls, mock_send_to_all):
    send_scheduled_notification("bogus")
    mock_send_to_all.assert_not_called()


def test_notification_content_keys():
    assert "morning" in NOTIFICATION_CONTENT
    assert "evening" in NOTIFICATION_CONTENT
    for kind in ("morning", "evening"):
        content = NOTIFICATION_CONTENT[kind]
        assert "title" in content
        assert "body" in content
        assert "url" in content


@patch("app.services.scheduler.scheduler")
def test_start_scheduler_adds_jobs(mock_scheduler):
    from app.services.scheduler import start_scheduler

    with patch("app.services.scheduler.settings") as mock_settings:
        mock_settings.user_tz = "America/New_York"
        mock_settings.morning_time = "08:00"
        mock_settings.evening_time = "20:00"
        start_scheduler()

    assert mock_scheduler.add_job.call_count == 2
    mock_scheduler.start.assert_called_once()

    calls = mock_scheduler.add_job.call_args_list
    assert calls[0].kwargs["id"] == "morning_push"
    assert calls[1].kwargs["id"] == "evening_push"
