from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models import (
    CheckIn,
    CheckInItem,
    DailyPlan,
    DailyPlanItem,
    DailySummary,
    ReflectionMessage,
    Task,
)
from app.services.summary import (
    backfill_summaries,
    format_summaries_for_prompt,
    gather_day_data,
    generate_summary,
    get_recent_summaries,
)


def _seed_day(db, for_date="2026-09-20", done_titles=None, not_done_titles=None, note=None):
    """Create a completed check-in with items for the given date."""
    done_titles = done_titles or ["Exercise"]
    not_done_titles = not_done_titles or ["Read"]

    tasks = []
    for title in done_titles + not_done_titles:
        t = Task(title=title, category="personal", sort_order=0.0)
        db.add(t)
        tasks.append(t)
    db.flush()

    check_in = CheckIn(
        for_date=for_date,
        status="completed",
        completed_at=datetime(2026, 9, 20, 23, 0, tzinfo=timezone.utc),
        note=note,
    )
    db.add(check_in)
    db.flush()

    for i, title in enumerate(done_titles):
        db.add(CheckInItem(
            check_in_id=check_in.id,
            task_id=tasks[i].id,
            task_title=title,
            task_category="personal",
            done=True,
        ))
    for i, title in enumerate(not_done_titles):
        db.add(CheckInItem(
            check_in_id=check_in.id,
            task_id=tasks[len(done_titles) + i].id,
            task_title=title,
            task_category="personal",
            done=False,
        ))
    db.commit()
    return check_in, tasks


class TestGatherDayData:
    def test_returns_none_for_no_checkin(self, db_session):
        result = gather_day_data(db_session, "2026-09-20")
        assert result is None

    def test_returns_none_for_pending_checkin(self, db_session):
        db_session.add(CheckIn(for_date="2026-09-20", status="pending"))
        db_session.commit()
        result = gather_day_data(db_session, "2026-09-20")
        assert result is None

    def test_returns_data_for_completed_checkin(self, db_session):
        _seed_day(db_session, "2026-09-20", done_titles=["Exercise"], not_done_titles=["Read"])
        result = gather_day_data(db_session, "2026-09-20")
        assert result is not None
        assert "Exercise" in result
        assert "Read" in result
        assert "Completed:" in result
        assert "Not completed:" in result

    def test_includes_checkin_note(self, db_session):
        _seed_day(db_session, "2026-09-20", note="Busy day at work")
        result = gather_day_data(db_session, "2026-09-20")
        assert "Busy day at work" in result

    def test_includes_plan_items(self, db_session):
        check_in, tasks = _seed_day(db_session, "2026-09-20")
        plan = DailyPlan(for_date="2026-09-20", status="confirmed")
        db_session.add(plan)
        db_session.flush()
        db_session.add(DailyPlanItem(
            plan_id=plan.id,
            task_id=tasks[0].id,
            task_title="Exercise",
            task_category="personal",
            is_key=True,
        ))
        db_session.commit()

        result = gather_day_data(db_session, "2026-09-20")
        assert "Morning plan:" in result
        assert "(key focus)" in result

    def test_includes_reflection_messages(self, db_session):
        check_in, _ = _seed_day(db_session, "2026-09-20")
        db_session.add(ReflectionMessage(
            check_in_id=check_in.id, role="assistant", content="Great job today!"
        ))
        db_session.add(ReflectionMessage(
            check_in_id=check_in.id, role="user", content="Thanks, feeling good."
        ))
        db_session.commit()

        result = gather_day_data(db_session, "2026-09-20")
        assert "Reflection conversation:" in result
        assert "Great job today!" in result
        assert "Thanks, feeling good." in result


class TestGenerateSummary:
    @patch("app.services.summary.complete")
    def test_generates_and_stores(self, mock_complete, db_session):
        mock_complete.return_value = "They exercised but did not read."
        _seed_day(db_session, "2026-09-20")

        result = generate_summary(db_session, "2026-09-20")
        assert result is not None
        assert result.summary_text == "They exercised but did not read."
        assert result.for_date == "2026-09-20"

        stored = db_session.query(DailySummary).filter_by(for_date="2026-09-20").first()
        assert stored is not None
        assert stored.summary_text == "They exercised but did not read."

    @patch("app.services.summary.complete")
    def test_skips_existing_summary(self, mock_complete, db_session):
        _seed_day(db_session, "2026-09-20")
        db_session.add(DailySummary(
            for_date="2026-09-20",
            summary_text="Already exists.",
            model_used="test",
        ))
        db_session.commit()

        result = generate_summary(db_session, "2026-09-20")
        assert result.summary_text == "Already exists."
        mock_complete.assert_not_called()

    def test_skips_date_with_no_checkin(self, db_session):
        result = generate_summary(db_session, "2026-09-20")
        assert result is None

    @patch("app.services.summary.complete", side_effect=Exception("Ollama down"))
    def test_handles_llm_failure(self, mock_complete, db_session):
        _seed_day(db_session, "2026-09-20")
        result = generate_summary(db_session, "2026-09-20")
        assert result is None
        assert db_session.query(DailySummary).count() == 0

    @patch("app.services.summary.complete", return_value="")
    def test_handles_empty_response(self, mock_complete, db_session):
        _seed_day(db_session, "2026-09-20")
        result = generate_summary(db_session, "2026-09-20")
        assert result is None


class TestGetRecentSummaries:
    def test_returns_summaries_before_date(self, db_session):
        for day in range(15, 22):
            db_session.add(DailySummary(
                for_date=f"2026-09-{day:02d}",
                summary_text=f"Day {day}",
                model_used="test",
            ))
        db_session.commit()

        results = get_recent_summaries(db_session, "2026-09-21", n=3)
        assert len(results) == 3
        assert results[0].for_date == "2026-09-20"
        assert results[1].for_date == "2026-09-19"
        assert results[2].for_date == "2026-09-18"

    def test_excludes_target_date(self, db_session):
        db_session.add(DailySummary(
            for_date="2026-09-20",
            summary_text="Today",
            model_used="test",
        ))
        db_session.commit()

        results = get_recent_summaries(db_session, "2026-09-20")
        assert len(results) == 0

    def test_returns_empty_when_no_summaries(self, db_session):
        results = get_recent_summaries(db_session, "2026-09-20")
        assert results == []


class TestFormatSummariesForPrompt:
    def test_formats_chronologically(self):
        s1 = MagicMock(for_date="2026-09-18", summary_text="Day 18 summary.")
        s2 = MagicMock(for_date="2026-09-19", summary_text="Day 19 summary.")
        s3 = MagicMock(for_date="2026-09-20", summary_text="Day 20 summary.")

        result = format_summaries_for_prompt([s3, s2, s1])
        assert result.startswith("Recent days:")
        lines = result.split("\n")
        assert "2026-09-18" in lines[1]
        assert "2026-09-19" in lines[2]
        assert "2026-09-20" in lines[3]

    def test_empty_list_returns_empty_string(self):
        assert format_summaries_for_prompt([]) == ""


class TestBackfillSummaries:
    @patch("app.services.summary.complete")
    def test_backfills_missing_summaries(self, mock_complete, db_session):
        mock_complete.return_value = "Summary text."
        _seed_day(db_session, "2026-09-18")
        _seed_day(db_session, "2026-09-19")
        db_session.add(DailySummary(
            for_date="2026-09-18",
            summary_text="Already exists.",
            model_used="test",
        ))
        db_session.commit()

        count = backfill_summaries(db_session)
        assert count == 1
        assert mock_complete.call_count == 1

        new_summary = db_session.query(DailySummary).filter_by(for_date="2026-09-19").first()
        assert new_summary is not None

    def test_backfill_with_no_data(self, db_session):
        count = backfill_summaries(db_session)
        assert count == 0


class TestSummariesEndpoint:
    def test_list_summaries(self, client, db_session):
        for day in range(15, 22):
            db_session.add(DailySummary(
                for_date=f"2026-09-{day:02d}",
                summary_text=f"Day {day}",
                model_used="test",
            ))
        db_session.commit()

        res = client.get("/api/summaries?days=3")
        assert res.status_code == 200
        data = res.json()
        assert len(data["summaries"]) == 3
        assert data["summaries"][0]["for_date"] == "2026-09-21"

    def test_list_summaries_empty(self, client, db_session):
        res = client.get("/api/summaries")
        assert res.status_code == 200
        assert len(res.json()["summaries"]) == 0


class TestPromptInjection:
    def test_reflection_prompt_includes_summaries(self, db_session):
        from app.services.reflection import build_system_prompt

        check_in, _ = _seed_day(db_session, "2026-09-20")
        db_session.add(DailySummary(
            for_date="2026-09-19",
            summary_text="Yesterday they completed all tasks.",
            model_used="test",
        ))
        db_session.commit()

        prompt = build_system_prompt(check_in, db_session)
        assert "Recent days:" in prompt
        assert "Yesterday they completed all tasks." in prompt

    def test_reflection_prompt_works_without_summaries(self, db_session):
        from app.services.reflection import build_system_prompt

        check_in, _ = _seed_day(db_session, "2026-09-20")
        prompt = build_system_prompt(check_in, db_session)
        assert "Recent days:" not in prompt
        assert "AcctBud" in prompt

    def test_planning_prompt_includes_summaries(self, db_session):
        from app.services.planning import build_planning_prompt

        tasks = [
            Task(title="Work task 1", category="work", sort_order=0.0),
        ]
        db_session.add_all(tasks)
        db_session.add(DailySummary(
            for_date="2026-09-19",
            summary_text="Yesterday went well.",
            model_used="test",
        ))
        db_session.commit()

        prompt = build_planning_prompt(
            tasks, None, None, db=db_session, for_date="2026-09-20"
        )
        assert "Recent days:" in prompt
        assert "Yesterday went well." in prompt

    def test_planning_prompt_works_without_db(self):
        from app.services.planning import build_planning_prompt

        prompt = build_planning_prompt([], None, None)
        assert "Recent days:" not in prompt
        assert "Suggest" in prompt
