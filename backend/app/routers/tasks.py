from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_db
from app.models.models import Task, Lead, User
from app.core.security import get_current_user
from app.schemas.schemas import TaskCreate, TaskOut, TaskUpdate
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])
templates = Jinja2Templates(directory="templates")

@router.post("/", response_model=TaskOut)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task."""
    new_task = Task(
        user_id=current_user.id,
        **task.dict()
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

@router.get("/", response_model=List[TaskOut])
async def list_tasks(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List tasks for the current user, optionally filtered by date."""
    stmt = select(Task).where(Task.user_id == current_user.id).options(selectinload(Task.lead))
    
    if start_date:
        stmt = stmt.where(Task.due_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        stmt = stmt.where(Task.due_date <= datetime.combine(end_date, datetime.max.time()))
    
    stmt = stmt.order_by(Task.due_date.asc())
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    
    # Map lead company name for convenience
    task_outs = []
    for t in tasks:
        out = TaskOut.from_orm(t)
        if t.lead:
            out.lead_company = t.lead.company_name
        task_outs.append(out)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "task_list_partial.html", 
            {"request": request, "tasks": task_outs, "now": datetime.utcnow()}
        )
    
    return task_outs

@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a task."""
    stmt = select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    res = await db.execute(stmt)
    task = res.scalars().first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task_data.dict(exclude_unset=True).items():
        setattr(task, key, value)
    
    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task."""
    stmt = delete(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    await db.execute(stmt)
    await db.commit()
    return {"detail": "Task deleted"}
