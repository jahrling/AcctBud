import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

from app.models import CheckIn, CheckInItem, ReflectionMessage, Task
from app.services.reflection import build_system_prompt


def _seed_completed_checkin(db, task_count=3, done_ids=None, note=None):
    tasks = []
    for i in range(task_count):
        t = Task(
            title=f"Task {i + 1}",
            category="work" if i % 2 == 0 else "personal",
            sort_order=float(i),
        )
        db.add(t)
        tasks.append(t)
    db.flush()

    ci = CheckIn(
        for_date="2026-08-19",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        note=note,
    )
    db.add(ci)
    db.flush()

    if done_ids is None:
        done_ids = {tasks[0].id} if tasks else set()

    for t in tasks:
        item = CheckInItem(
            check_in_id=ci.id,
            task_id=t.id,
            task_title=t.title,
            task_category=t.category,
            done=t.id in done_ids,
        )
        db.add(item)
    db.commit()
    db.refresh(ci)
    return ci, tasks


def _mock_stream(*args, **kwargs):
    tokens = ["Great ", "job ", "today!"]
    yield from tokens


class TestSystemPrompt:
    def test_includes_done_tasks(self, db_session):
        ci, tasks = _seed_completed_checkin(db_session)
        prompt = build_system_prompt(ci)
        assert "Task 1" in prompt
        assert "Completed tasks" in prompt

    def test_includes_not_done_tasks(self, db_session):
        ci, tasks = _seed_completed_checkin(db_session, done_ids=set())
        prompt = build_system_prompt(ci)
        assert "Not completed" in prompt

    def test_includes_note(self, db_session):
        ci, _ = _seed_completed_checkin(db_session, note="Rough day")
        prompt = build_system_prompt(ci)
        assert "Rough day" in prompt

    def test_no_tasks(self, db_session):
        ci, _ = _seed_completed_checkin(db_session, task_count=0)
        prompt = build_system_prompt(ci)
        assert "No tasks were active" in prompt


class TestGetReflection:
    def test_returns_empty_for_new_checkin(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        res = client.get(f"/api/reflections/{ci.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["messages"] == []
        assert data["finished"] is False

    def test_returns_messages_excluding_system(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        for role, content in [
            ("system", "You are AcctBud"),
            ("assistant", "Great job!"),
            ("user", "Thanks"),
        ]:
            db_session.add(
                ReflectionMessage(
                    check_in_id=ci.id, role=role, content=content
                )
            )
        db_session.commit()

        res = client.get(f"/api/reflections/{ci.id}")
        data = res.json()
        assert len(data["messages"]) == 2
        roles = [m["role"] for m in data["messages"]]
        assert "system" not in roles

    def test_not_found(self, client):
        res = client.get("/api/reflections/999")
        assert res.status_code == 404


class TestReflectionChat:
    def _mock_session_local(self, db_session):
        real_close = db_session.close
        db_session.close = lambda: None
        mock_cls = lambda: db_session  # noqa: E731
        return mock_cls, real_close

    def test_start_conversation(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        mock_session_local, _ = self._mock_session_local(db_session)

        with (
            patch("app.routers.reflections.stream_chat", side_effect=_mock_stream),
            patch("app.routers.reflections.SessionLocal", mock_session_local),
        ):
            res = client.post(
                f"/api/reflections/{ci.id}/chat",
                json={"message": None},
            )
        assert res.status_code == 200

        events = res.text.strip().split("\n\n")
        token_events = [e for e in events if e.startswith("event: token")]
        done_events = [e for e in events if e.startswith("event: done")]
        assert len(token_events) == 3
        assert len(done_events) == 1

        msgs = (
            db_session.query(ReflectionMessage)
            .filter(ReflectionMessage.check_in_id == ci.id)
            .all()
        )
        roles = {m.role for m in msgs}
        assert "system" in roles
        assert "assistant" in roles
        assistant_msg = next(m for m in msgs if m.role == "assistant")
        assert assistant_msg.content == "Great job today!"

    def test_continue_conversation(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        db_session.add(
            ReflectionMessage(
                check_in_id=ci.id, role="system", content="You are AcctBud"
            )
        )
        db_session.add(
            ReflectionMessage(
                check_in_id=ci.id, role="assistant", content="Hello!"
            )
        )
        db_session.commit()
        mock_session_local, _ = self._mock_session_local(db_session)

        with (
            patch("app.routers.reflections.stream_chat", side_effect=_mock_stream),
            patch("app.routers.reflections.SessionLocal", mock_session_local),
        ):
            res = client.post(
                f"/api/reflections/{ci.id}/chat",
                json={"message": "I felt good about today"},
            )
        assert res.status_code == 200

        user_msgs = (
            db_session.query(ReflectionMessage)
            .filter(
                ReflectionMessage.check_in_id == ci.id,
                ReflectionMessage.role == "user",
            )
            .all()
        )
        assert len(user_msgs) == 1
        assert user_msgs[0].content == "I felt good about today"

    def test_requires_completed_checkin(self, client, db_session):
        ci = CheckIn(for_date="2026-08-19", status="pending")
        db_session.add(ci)
        db_session.commit()

        res = client.post(
            f"/api/reflections/{ci.id}/chat", json={"message": None}
        )
        assert res.status_code == 409

    def test_requires_unfinished_reflection(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        ci.reflection_finished = True
        db_session.commit()

        res = client.post(
            f"/api/reflections/{ci.id}/chat", json={"message": None}
        )
        assert res.status_code == 409

    def test_ollama_connection_error(self, client, db_session):
        import httpx

        ci, _ = _seed_completed_checkin(db_session)
        mock_session_local, _ = self._mock_session_local(db_session)

        def _error_stream(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with (
            patch("app.routers.reflections.stream_chat", side_effect=_error_stream),
            patch("app.routers.reflections.SessionLocal", mock_session_local),
        ):
            res = client.post(
                f"/api/reflections/{ci.id}/chat", json={"message": None}
            )
        assert res.status_code == 200
        assert "event: error" in res.text


class TestReflectionFinish:
    def test_writes_journal(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        db_session.add(
            ReflectionMessage(
                check_in_id=ci.id, role="assistant", content="Great job!"
            )
        )
        db_session.add(
            ReflectionMessage(
                check_in_id=ci.id, role="user", content="Thanks!"
            )
        )
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.journal.settings") as mock_settings:
                mock_settings.journal_path = tmpdir

                res = client.post(f"/api/reflections/{ci.id}/finish")
                assert res.status_code == 200
                assert res.json()["journal_written"] is True

                path = os.path.join(tmpdir, "2026", "08", "19-reflection.md")
                assert os.path.exists(path)

                content = open(path).read()
                assert "type: reflection" in content
                assert "**AcctBud:** Great job!" in content
                assert "**Me:** Thanks!" in content

                db_session.refresh(ci)
                assert ci.reflection_finished is True

    def test_vault_locked_degrades_gracefully(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        db_session.add(
            ReflectionMessage(
                check_in_id=ci.id, role="assistant", content="Hello"
            )
        )
        db_session.commit()

        with patch("app.services.journal.settings") as mock_settings:
            mock_settings.journal_path = "/nonexistent/vault/locked"
            res = client.post(f"/api/reflections/{ci.id}/finish")
            assert res.status_code == 200
            assert res.json()["journal_written"] is False

    def test_no_messages_returns_409(self, client, db_session):
        ci, _ = _seed_completed_checkin(db_session)
        res = client.post(f"/api/reflections/{ci.id}/finish")
        assert res.status_code == 409


class TestReflectionJournal:
    def test_render_includes_conversation(self, db_session):
        from app.services.journal import _render_reflection_entry

        ci, _ = _seed_completed_checkin(db_session)
        messages = [
            ReflectionMessage(
                check_in_id=ci.id, role="assistant", content="Nice work!"
            ),
            ReflectionMessage(
                check_in_id=ci.id, role="user", content="It was a good day."
            ),
        ]
        output = _render_reflection_entry(ci, messages)
        assert "**AcctBud:** Nice work!" in output
        assert "**Me:** It was a good day." in output

    def test_frontmatter_has_type_reflection(self, db_session):
        from app.services.journal import _render_reflection_entry

        ci, _ = _seed_completed_checkin(db_session)
        messages = [
            ReflectionMessage(
                check_in_id=ci.id, role="assistant", content="Hello"
            ),
        ]
        output = _render_reflection_entry(ci, messages)
        assert "type: reflection" in output
        assert f"check_in_id: {ci.id}" in output

    def test_retry_pending_reflections(self, db_session):
        from app.services.journal import retry_pending_reflections

        ci, _ = _seed_completed_checkin(db_session)
        ci.reflection_finished = True
        ci.reflection_journal_written = False
        db_session.add(
            ReflectionMessage(
                check_in_id=ci.id, role="assistant", content="Hello"
            )
        )
        db_session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.journal.settings") as mock_settings:
                mock_settings.journal_path = tmpdir
                written = retry_pending_reflections(db_session)
                assert written == 1

                db_session.refresh(ci)
                assert ci.reflection_journal_written is True

                path = os.path.join(tmpdir, "2026", "08", "19-reflection.md")
                assert os.path.exists(path)
