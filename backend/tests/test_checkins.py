import os
import tempfile

from app.models import CheckIn, CheckInItem, Task


def _seed_tasks(db, count=3):
    tasks = []
    for i in range(count):
        t = Task(
            title=f"Task {i + 1}",
            category="work" if i % 2 == 0 else "personal",
            sort_order=float(i),
        )
        db.add(t)
        tasks.append(t)
    db.commit()
    for t in tasks:
        db.refresh(t)
    return tasks


class TestGetTodayCheckIn:
    def test_creates_checkin_on_first_access(self, client, db_session):
        _seed_tasks(db_session, 3)
        res = client.get("/api/checkins/today")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "pending"
        assert len(data["items"]) == 3

    def test_returns_existing_checkin_on_second_access(self, client, db_session):
        _seed_tasks(db_session, 2)
        first = client.get("/api/checkins/today").json()
        second = client.get("/api/checkins/today").json()
        assert first["id"] == second["id"]

    def test_no_tasks_creates_empty_checkin(self, client):
        res = client.get("/api/checkins/today")
        assert res.status_code == 200
        assert len(res.json()["items"]) == 0

    def test_only_active_tasks_are_snapshotted(self, client, db_session):
        tasks = _seed_tasks(db_session, 3)
        tasks[1].status = "paused"
        db_session.commit()

        res = client.get("/api/checkins/today")
        item_task_ids = {i["task_id"] for i in res.json()["items"]}
        assert tasks[1].id not in item_task_ids
        assert len(res.json()["items"]) == 2


class TestSnapshotSemantics:
    def test_task_edited_after_checkin_does_not_alter_snapshot(self, client, db_session):
        tasks = _seed_tasks(db_session, 2)
        checkin = client.get("/api/checkins/today").json()

        tasks[0].title = "Renamed"
        db_session.commit()

        items = client.get("/api/checkins/today").json()["items"]
        assert items[0]["task_title"] == "Task 1"

    def test_task_archived_after_checkin_does_not_alter_snapshot(self, client, db_session):
        tasks = _seed_tasks(db_session, 2)
        client.get("/api/checkins/today")

        tasks[0].status = "archived"
        db_session.commit()

        items = client.get("/api/checkins/today").json()["items"]
        assert len(items) == 2


class TestCompleteCheckIn:
    def test_complete_with_some_done(self, client, db_session):
        tasks = _seed_tasks(db_session, 3)
        checkin = client.get("/api/checkins/today").json()

        res = client.post(
            f"/api/checkins/{checkin['id']}/complete",
            json={"done_task_ids": [tasks[0].id, tasks[2].id]},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

        done_ids = {i["task_id"] for i in data["items"] if i["done"]}
        assert done_ids == {tasks[0].id, tasks[2].id}

    def test_complete_with_none_done(self, client, db_session):
        _seed_tasks(db_session, 3)
        checkin = client.get("/api/checkins/today").json()

        res = client.post(
            f"/api/checkins/{checkin['id']}/complete",
            json={"done_task_ids": []},
        )
        data = res.json()
        assert data["status"] == "completed"
        assert all(not i["done"] for i in data["items"])

    def test_complete_with_note(self, client, db_session):
        _seed_tasks(db_session, 1)
        checkin = client.get("/api/checkins/today").json()

        res = client.post(
            f"/api/checkins/{checkin['id']}/complete",
            json={"done_task_ids": [], "note": "Rough day"},
        )
        assert res.json()["note"] == "Rough day"

    def test_idempotent_resubmission_updates(self, client, db_session):
        tasks = _seed_tasks(db_session, 3)
        checkin = client.get("/api/checkins/today").json()

        client.post(
            f"/api/checkins/{checkin['id']}/complete",
            json={"done_task_ids": [tasks[0].id]},
        )
        res = client.post(
            f"/api/checkins/{checkin['id']}/complete",
            json={"done_task_ids": [tasks[1].id, tasks[2].id], "note": "Updated"},
        )
        data = res.json()
        done_ids = {i["task_id"] for i in data["items"] if i["done"]}
        assert done_ids == {tasks[1].id, tasks[2].id}
        assert data["note"] == "Updated"

    def test_complete_not_found(self, client):
        res = client.post("/api/checkins/999/complete", json={"done_task_ids": []})
        assert res.status_code == 404


class TestCheckInHistory:
    def test_list_returns_recent_checkins(self, client, db_session):
        ci1 = CheckIn(for_date="2026-08-17", status="completed")
        ci2 = CheckIn(for_date="2026-08-18", status="missed")
        db_session.add_all([ci1, ci2])
        db_session.commit()

        res = client.get("/api/checkins?limit=10")
        data = res.json()
        assert len(data["checkins"]) == 2
        assert data["checkins"][0]["for_date"] == "2026-08-18"

    def test_list_respects_limit(self, client, db_session):
        for i in range(5):
            db_session.add(CheckIn(for_date=f"2026-08-{10 + i:02d}"))
        db_session.commit()

        res = client.get("/api/checkins?limit=3")
        assert len(res.json()["checkins"]) == 3


class TestNoneDoneVsMissed:
    def test_none_done_is_completed_not_missed(self, client, db_session):
        _seed_tasks(db_session, 2)
        checkin = client.get("/api/checkins/today").json()

        res = client.post(
            f"/api/checkins/{checkin['id']}/complete",
            json={"done_task_ids": []},
        )
        assert res.json()["status"] == "completed"

    def test_unanswered_stays_pending(self, client, db_session):
        _seed_tasks(db_session, 2)
        checkin = client.get("/api/checkins/today").json()
        assert checkin["status"] == "pending"


class TestJournalWriter:
    def test_journal_written_on_complete(self, client, db_session):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.journal.settings") as mock_settings:
                mock_settings.journal_path = tmpdir

                tasks = _seed_tasks(db_session, 2)
                checkin = client.get("/api/checkins/today").json()
                client.post(
                    f"/api/checkins/{checkin['id']}/complete",
                    json={"done_task_ids": [tasks[0].id], "note": "Good day"},
                )

                from app.services.checkins import today_str

                today = today_str("UTC")
                parts = today.split("-")
                path = os.path.join(tmpdir, parts[0], parts[1], f"{parts[2]}-checkin.md")
                assert os.path.exists(path)

                content = open(path).read()
                assert "type: checkin" in content
                assert "Task 1" in content
                assert "Good day" in content

    def test_journal_failure_does_not_block_checkin(self, client, db_session):
        from unittest.mock import patch

        with patch("app.services.journal.settings") as mock_settings:
            mock_settings.journal_path = "/nonexistent/vault/locked"

            _seed_tasks(db_session, 1)
            checkin = client.get("/api/checkins/today").json()
            res = client.post(
                f"/api/checkins/{checkin['id']}/complete",
                json={"done_task_ids": []},
            )
            assert res.status_code == 200
            assert res.json()["status"] == "completed"

            ci = db_session.query(CheckIn).filter(CheckIn.id == checkin["id"]).first()
            assert ci.journal_written is False

    def test_retry_writes_pending_entries(self, db_session):
        from unittest.mock import patch
        from app.services.journal import retry_pending_entries

        tasks = _seed_tasks(db_session, 1)
        ci = CheckIn(for_date="2026-08-15", status="completed", journal_written=False)
        db_session.add(ci)
        db_session.flush()
        item = CheckInItem(
            check_in_id=ci.id,
            task_id=tasks[0].id,
            task_title=tasks[0].title,
            task_category=tasks[0].category,
            done=True,
        )
        db_session.add(item)
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.journal.settings") as mock_settings:
                mock_settings.journal_path = tmpdir
                written = retry_pending_entries(db_session)
                assert written == 1

                db_session.refresh(ci)
                assert ci.journal_written is True

                path = os.path.join(tmpdir, "2026", "08", "15-checkin.md")
                assert os.path.exists(path)


class TestFollowupAndRollover:
    def _patch_session(self, db_session):
        """Prevent scheduler's finally-close from detaching test objects."""
        from unittest.mock import patch, MagicMock

        real_close = db_session.close
        db_session.close = lambda: None
        mock_session_cls = MagicMock(return_value=db_session)
        return mock_session_cls, real_close

    def test_followup_fires_once(self, db_session):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        from app.services.scheduler import send_followup_nag

        ci = CheckIn(
            for_date="2026-08-19",
            status="pending",
            notified_at=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        db_session.add(ci)
        db_session.commit()

        mock_session_cls, _ = self._patch_session(db_session)
        with (
            patch("app.services.scheduler.SessionLocal", mock_session_cls),
            patch("app.services.scheduler.send_to_all", return_value=["sent"]),
        ):
            send_followup_nag()
            db_session.refresh(ci)
            assert ci.followup_at is not None

            first_followup = ci.followup_at
            send_followup_nag()
            db_session.refresh(ci)
            assert ci.followup_at == first_followup

    def test_followup_does_not_fire_before_2h(self, db_session):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        from app.services.scheduler import send_followup_nag

        ci = CheckIn(
            for_date="2026-08-19",
            status="pending",
            notified_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add(ci)
        db_session.commit()

        mock_session_cls, _ = self._patch_session(db_session)
        with (
            patch("app.services.scheduler.SessionLocal", mock_session_cls),
            patch("app.services.scheduler.send_to_all") as mock_send,
        ):
            send_followup_nag()
            mock_send.assert_not_called()
            db_session.refresh(ci)
            assert ci.followup_at is None

    def test_rollover_marks_pending_as_missed(self, db_session):
        from unittest.mock import patch
        from app.services.scheduler import rollover_missed

        ci = CheckIn(for_date="2026-08-17", status="pending")
        db_session.add(ci)
        db_session.commit()

        mock_session_cls, _ = self._patch_session(db_session)
        with (
            patch("app.services.scheduler.SessionLocal", mock_session_cls),
            patch("app.services.scheduler.today_str", return_value="2026-08-19"),
        ):
            rollover_missed()
            db_session.refresh(ci)
            assert ci.status == "missed"

    def test_rollover_does_not_touch_completed(self, db_session):
        from unittest.mock import patch
        from app.services.scheduler import rollover_missed

        ci = CheckIn(for_date="2026-08-17", status="completed")
        db_session.add(ci)
        db_session.commit()

        mock_session_cls, _ = self._patch_session(db_session)
        with (
            patch("app.services.scheduler.SessionLocal", mock_session_cls),
            patch("app.services.scheduler.today_str", return_value="2026-08-19"),
        ):
            rollover_missed()
            db_session.refresh(ci)
            assert ci.status == "completed"

    def test_rollover_does_not_touch_today(self, db_session):
        from unittest.mock import patch
        from app.services.scheduler import rollover_missed

        ci = CheckIn(for_date="2026-08-19", status="pending")
        db_session.add(ci)
        db_session.commit()

        mock_session_cls, _ = self._patch_session(db_session)
        with (
            patch("app.services.scheduler.SessionLocal", mock_session_cls),
            patch("app.services.scheduler.today_str", return_value="2026-08-19"),
        ):
            rollover_missed()
            db_session.refresh(ci)
            assert ci.status == "pending"
