from app.models import Task


def test_create_task(client):
    res = client.post("/api/tasks", json={"title": "Ship feature", "category": "work"})
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Ship feature"
    assert data["category"] == "work"
    assert data["status"] == "active"
    assert data["note"] is None


def test_create_task_with_note(client):
    res = client.post(
        "/api/tasks",
        json={"title": "Buy groceries", "category": "personal", "note": "milk, eggs"},
    )
    assert res.status_code == 201
    assert res.json()["note"] == "milk, eggs"


def test_create_task_validation_title_required(client):
    res = client.post("/api/tasks", json={"category": "work"})
    assert res.status_code == 422


def test_create_task_validation_title_too_long(client):
    res = client.post("/api/tasks", json={"title": "x" * 121, "category": "work"})
    assert res.status_code == 422


def test_create_task_validation_empty_title(client):
    res = client.post("/api/tasks", json={"title": "", "category": "work"})
    assert res.status_code == 422


def test_create_task_validation_bad_category(client):
    res = client.post("/api/tasks", json={"title": "Test", "category": "hobby"})
    assert res.status_code == 422


def test_list_tasks_default_active(client):
    client.post("/api/tasks", json={"title": "A", "category": "work"})
    client.post("/api/tasks", json={"title": "B", "category": "personal"})
    res = client.get("/api/tasks")
    data = res.json()
    assert len(data["tasks"]) == 2
    assert data["active_count"] == 2


def test_list_tasks_filters_by_status(client):
    client.post("/api/tasks", json={"title": "Active one", "category": "work"})
    r = client.post("/api/tasks", json={"title": "To pause", "category": "work"})
    task_id = r.json()["id"]
    client.patch(f"/api/tasks/{task_id}", json={"status": "paused"})

    active = client.get("/api/tasks?status=active").json()
    assert len(active["tasks"]) == 1
    assert active["active_count"] == 1

    paused = client.get("/api/tasks?status=paused").json()
    assert len(paused["tasks"]) == 1
    assert paused["active_count"] == 1


def test_list_tasks_all(client):
    client.post("/api/tasks", json={"title": "A", "category": "work"})
    r = client.post("/api/tasks", json={"title": "B", "category": "work"})
    client.patch(f"/api/tasks/{r.json()['id']}", json={"status": "archived"})

    all_tasks = client.get("/api/tasks?status=all").json()
    assert len(all_tasks["tasks"]) == 2
    assert all_tasks["active_count"] == 1


def test_update_task(client):
    r = client.post("/api/tasks", json={"title": "Old", "category": "work"})
    task_id = r.json()["id"]

    res = client.patch(
        f"/api/tasks/{task_id}",
        json={"title": "New", "category": "personal", "note": "details"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "New"
    assert data["category"] == "personal"
    assert data["note"] == "details"


def test_update_task_not_found(client):
    res = client.patch("/api/tasks/999", json={"title": "Nope"})
    assert res.status_code == 404


def test_archive_not_delete(client, db_session):
    r = client.post("/api/tasks", json={"title": "Temp", "category": "work"})
    task_id = r.json()["id"]
    client.patch(f"/api/tasks/{task_id}", json={"status": "archived"})

    task = db_session.query(Task).filter(Task.id == task_id).first()
    assert task is not None
    assert task.status == "archived"


def test_update_sort_order(client):
    r1 = client.post("/api/tasks", json={"title": "First", "category": "work"})
    r2 = client.post("/api/tasks", json={"title": "Second", "category": "work"})
    client.patch(f"/api/tasks/{r2.json()['id']}", json={"sort_order": -1.0})

    tasks = client.get("/api/tasks").json()["tasks"]
    assert tasks[0]["title"] == "Second"
    assert tasks[1]["title"] == "First"


def test_update_bad_status(client):
    r = client.post("/api/tasks", json={"title": "T", "category": "work"})
    res = client.patch(f"/api/tasks/{r.json()['id']}", json={"status": "deleted"})
    assert res.status_code == 422
