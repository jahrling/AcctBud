import os
import tempfile

from unittest.mock import patch

from app.models import CheckIn, CheckInItem, DailyPlan, DailyPlanItem, Task


def _seed_tasks(db, work=2, personal=2):
    tasks = []
    for i in range(work):
        t = Task(title=f"Work task {i + 1}", category="work", sort_order=float(i))
        db.add(t)
        tasks.append(t)
    for i in range(personal):
        t = Task(title=f"Personal task {i + 1}", category="personal", sort_order=float(work + i))
        db.add(t)
        tasks.append(t)
    db.commit()
    for t in tasks:
        db.refresh(t)
    return tasks


class TestGetTodayPlan:
    def test_creates_draft_plan(self, client, db_session):
        _seed_tasks(db_session)
        res = client.get("/api/plans/today")
        assert res.status_code == 200
        data = res.json()
        assert data["plan"]["status"] == "draft"
        assert data["plan"]["items"] == []
        assert len(data["active_tasks"]) == 4

    def test_returns_existing_plan(self, client, db_session):
        _seed_tasks(db_session)
        first = client.get("/api/plans/today").json()
        second = client.get("/api/plans/today").json()
        assert first["plan"]["id"] == second["plan"]["id"]


class TestConfirmPlan:
    def test_confirm_valid_plan(self, client, db_session):
        tasks = _seed_tasks(db_session)
        plan = client.get("/api/plans/today").json()["plan"]

        res = client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": tasks[0].id, "is_key": True},
                    {"task_id": tasks[2].id, "is_key": True},
                ]
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "confirmed"
        assert data["confirmed_at"] is not None
        assert len(data["items"]) == 2

    def test_confirm_rejects_missing_key_work(self, client, db_session):
        tasks = _seed_tasks(db_session)
        plan = client.get("/api/plans/today").json()["plan"]

        res = client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": tasks[0].id, "is_key": False},
                    {"task_id": tasks[2].id, "is_key": True},
                ]
            },
        )
        assert res.status_code == 422
        assert "key work" in res.json()["detail"].lower()

    def test_confirm_rejects_missing_key_personal(self, client, db_session):
        tasks = _seed_tasks(db_session)
        plan = client.get("/api/plans/today").json()["plan"]

        res = client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": tasks[0].id, "is_key": True},
                    {"task_id": tasks[2].id, "is_key": False},
                ]
            },
        )
        assert res.status_code == 422
        assert "key" in res.json()["detail"].lower()

    def test_confirm_rejects_over_five_items(self, client, db_session):
        tasks = _seed_tasks(db_session, work=4, personal=4)
        plan = client.get("/api/plans/today").json()["plan"]

        res = client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": t.id, "is_key": i < 2}
                    for i, t in enumerate(tasks[:6])
                ]
            },
        )
        assert res.status_code == 422

    def test_confirm_idempotent(self, client, db_session):
        tasks = _seed_tasks(db_session)
        plan = client.get("/api/plans/today").json()["plan"]

        items = [
            {"task_id": tasks[0].id, "is_key": True},
            {"task_id": tasks[2].id, "is_key": True},
        ]
        client.post(f"/api/plans/{plan['id']}/confirm", json={"items": items})

        items2 = [
            {"task_id": tasks[0].id, "is_key": True},
            {"task_id": tasks[2].id, "is_key": True},
            {"task_id": tasks[1].id, "is_key": False},
        ]
        res = client.post(f"/api/plans/{plan['id']}/confirm", json={"items": items2})
        assert res.status_code == 200
        assert len(res.json()["items"]) == 3

    def test_confirm_single_category_ok(self, client, db_session):
        tasks = _seed_tasks(db_session, work=0, personal=3)
        plan = client.get("/api/plans/today").json()["plan"]

        res = client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": tasks[0].id, "is_key": True},
                    {"task_id": tasks[1].id, "is_key": False},
                ]
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "confirmed"

    def test_confirm_single_category_still_needs_key(self, client, db_session):
        tasks = _seed_tasks(db_session, work=0, personal=3)
        plan = client.get("/api/plans/today").json()["plan"]

        res = client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": tasks[0].id, "is_key": False},
                ]
            },
        )
        assert res.status_code == 422
        assert "key" in res.json()["detail"].lower()

    def test_confirm_rejects_nonexistent_task(self, client, db_session):
        _seed_tasks(db_session)
        plan = client.get("/api/plans/today").json()["plan"]

        res = client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": 9999, "is_key": True},
                    {"task_id": 9998, "is_key": True},
                ]
            },
        )
        assert res.status_code == 422


class TestPlanCheckInIntegration:
    def test_checkin_uses_plan_items_when_confirmed(self, client, db_session):
        tasks = _seed_tasks(db_session, work=3, personal=3)
        plan = client.get("/api/plans/today").json()["plan"]

        client.post(
            f"/api/plans/{plan['id']}/confirm",
            json={
                "items": [
                    {"task_id": tasks[0].id, "is_key": True},
                    {"task_id": tasks[3].id, "is_key": True},
                ]
            },
        )

        checkin = client.get("/api/checkins/today").json()
        assert len(checkin["items"]) == 2
        item_ids = {i["task_id"] for i in checkin["items"]}
        assert item_ids == {tasks[0].id, tasks[3].id}

    def test_checkin_falls_back_without_plan(self, client, db_session):
        tasks = _seed_tasks(db_session, work=2, personal=2)
        checkin = client.get("/api/checkins/today").json()
        assert len(checkin["items"]) == 4


class TestPlanJournal:
    def test_journal_written_on_confirm(self, client, db_session):
        tasks = _seed_tasks(db_session)
        plan_data = client.get("/api/plans/today").json()["plan"]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.journal.settings") as mock_settings:
                mock_settings.journal_path = tmpdir

                res = client.post(
                    f"/api/plans/{plan_data['id']}/confirm",
                    json={
                        "items": [
                            {"task_id": tasks[0].id, "is_key": True},
                            {"task_id": tasks[2].id, "is_key": True},
                        ]
                    },
                )

                from app.services.checkins import today_str

                today = today_str("UTC")
                parts = today.split("-")
                path = os.path.join(tmpdir, parts[0], parts[1], f"{parts[2]}-plan.md")
                assert os.path.exists(path)

                content = open(path).read()
                assert "type: plan" in content
                assert "Work task 1" in content

    def test_retry_plan_journal(self, db_session):
        from app.services.journal import retry_pending_plan_entries

        tasks = _seed_tasks(db_session)
        plan = DailyPlan(for_date="2026-08-15", status="confirmed", journal_written=False)
        db_session.add(plan)
        db_session.flush()
        item = DailyPlanItem(
            plan_id=plan.id,
            task_id=tasks[0].id,
            task_title=tasks[0].title,
            task_category=tasks[0].category,
            is_key=True,
        )
        db_session.add(item)
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.journal.settings") as mock_settings:
                mock_settings.journal_path = tmpdir
                written = retry_pending_plan_entries(db_session)
                assert written == 1
                db_session.refresh(plan)
                assert plan.journal_written is True


class TestPlanRollover:
    def test_draft_plans_rolled_to_skipped(self, db_session):
        from unittest.mock import MagicMock
        from app.services.scheduler import rollover_missed

        plan = DailyPlan(for_date="2026-08-17", status="draft")
        db_session.add(plan)
        db_session.commit()

        mock_session_cls = MagicMock(return_value=db_session)
        db_session.close = lambda: None
        with (
            patch("app.services.scheduler.SessionLocal", mock_session_cls),
            patch("app.services.scheduler.today_str", return_value="2026-08-19"),
        ):
            rollover_missed()
            db_session.refresh(plan)
            assert plan.status == "skipped"

    def test_confirmed_plan_not_rolled(self, db_session):
        from unittest.mock import MagicMock
        from app.services.scheduler import rollover_missed

        plan = DailyPlan(for_date="2026-08-17", status="confirmed")
        db_session.add(plan)
        db_session.commit()

        mock_session_cls = MagicMock(return_value=db_session)
        db_session.close = lambda: None
        with (
            patch("app.services.scheduler.SessionLocal", mock_session_cls),
            patch("app.services.scheduler.today_str", return_value="2026-08-19"),
        ):
            rollover_missed()
            db_session.refresh(plan)
            assert plan.status == "confirmed"
