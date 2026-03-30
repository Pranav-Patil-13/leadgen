from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Union, Any
from fastapi.templating import Jinja2Templates
import os

from app.core.database import get_db
from app.models.models import LeadPipeline
from app.schemas.schemas import (
    LeadPipelineCreate, LeadPipelineOut, LeadPipelineUpdate
)

router = APIRouter(prefix="/api/pipelines", tags=["Pipelines"])
templates = Jinja2Templates(directory="templates")


from app.core.security import get_current_user
from app.models.models import User

@router.get("/", response_model=List[LeadPipelineOut])
async def list_pipelines(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all pipelines for a user. Returns HTML for HTMX or JSON for API."""
    result = await db.execute(
        select(LeadPipeline)
        .where(LeadPipeline.user_id == current_user.id)
        .order_by(LeadPipeline.created_at.desc())
    )
    pipelines = result.scalars().all()
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "pipeline_list.html", 
            {"request": request, "pipelines": pipelines}
        )
    
    return pipelines


@router.get("/{pipeline_id}", response_model=LeadPipelineOut)
async def get_pipeline(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single pipeline by ID."""
    result = await db.execute(
        select(LeadPipeline).where(LeadPipeline.id == pipeline_id, LeadPipeline.user_id == current_user.id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.post("/", response_model=LeadPipelineOut)
async def create_pipeline(
    pipeline: LeadPipelineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new lead pipeline."""
    db_pipeline = LeadPipeline(user_id=current_user.id, **pipeline.model_dump())
    db.add(db_pipeline)
    await db.commit()
    await db.refresh(db_pipeline)
    return db_pipeline


@router.put("/{pipeline_id}", response_model=LeadPipelineOut)
async def update_pipeline(
    pipeline_id: int,
    pipeline_update: LeadPipelineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a pipeline's configuration."""
    result = await db.execute(
        select(LeadPipeline).where(LeadPipeline.id == pipeline_id, LeadPipeline.user_id == current_user.id)
    )
    db_pipeline = result.scalar_one_or_none()
    if not db_pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    update_data = pipeline_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pipeline, key, value)

    await db.commit()
    await db.refresh(db_pipeline)
    return db_pipeline


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a pipeline."""
    result = await db.execute(
        select(LeadPipeline).where(LeadPipeline.id == pipeline_id, LeadPipeline.user_id == current_user.id)
    )
    db_pipeline = result.scalar_one_or_none()
    if not db_pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    await db.delete(db_pipeline)
    await db.commit()
    return {"detail": "Pipeline deleted"}

@router.post("/{pipeline_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_pipeline(
    pipeline_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """Triggers the scraper for this pipeline in the background via Celery."""
    from app.services.scraper_tasks import run_pipeline_task
    pipeline = await db.get(LeadPipeline, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Offload to Celery worker (more reliable for browser automation)
    run_pipeline_task.delay(pipeline_id)
    
    return {"status": "Scraping job queued", "pipeline": pipeline.name}
