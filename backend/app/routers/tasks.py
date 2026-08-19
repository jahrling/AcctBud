from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, utcnow
from app.schemas import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
def list_tasks(status: Literal["active", "paused", "archived", "all"] = "active", db: Session = Depends(get_db)):
    query = db.query(Task)
    if status != "all":
        query = query.filter(Task.status == status)
    tasks = query.order_by(Task.sort_order, Task.created_at).all()
    active_count = db.query(Task).filter(Task.status == "active").count()
    return TaskListResponse(tasks=tasks, active_count=active_count)


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    max_order = db.query(Task).filter(Task.status == "active").count()
    task = Task(
        title=body.title,
        category=body.category,
        note=body.note,
        sort_order=float(max_order),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, body: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task
