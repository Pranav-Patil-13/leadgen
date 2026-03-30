from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from typing import List, Optional, Union, Any
from datetime import datetime, timedelta
import json
from fastapi.templating import Jinja2Templates

from fastapi.responses import StreamingResponse
import csv
import io

from app.core.database import get_db
from app.models.models import Lead, LeadActivity, LeadPipeline, User, UserSettings
from app.core.security import get_current_user
from app.schemas.schemas import (
    LeadCreate, LeadOut, LeadUpdate,
    LeadActivityCreate, LeadActivityOut
)

router = APIRouter(prefix="/api/leads", tags=["Leads"])
templates = Jinja2Templates(directory="templates")

@router.get("/activities", response_model=Union[List[LeadActivityOut], Any])
async def list_all_activities(
    request: Request,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get the global activity timeline."""
    result = await db.execute(
        select(LeadActivity)
        .options(joinedload(LeadActivity.lead))
        .order_by(LeadActivity.created_at.desc())
        .limit(limit)
    )
    activities = result.scalars().all()

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "activity_feed.html", 
            {"request": request, "activities": activities}
        )
    
    return activities


@router.get("/", response_model=Union[List[LeadOut], Any])
async def list_leads(
    request: Request,
    pipeline_id: Optional[Union[int, str]] = Query(None),
    status: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    assigned_user_id: Optional[Union[int, str]] = Query(None),
    skip: int = 0,
    limit: int = 50,
    view: Optional[str] = Query(None), # table or board
    db: AsyncSession = Depends(get_db)
):
    """List leads with optional filters. Returns HTML for HTMX or JSON for API."""
    query = select(Lead).options(joinedload(Lead.assigned_to))
    
    # Handle potentially empty string IDs from HTMX
    if pipeline_id and str(pipeline_id).strip():
        query = query.where(Lead.pipeline_id == int(pipeline_id))
    if status:
        query = query.where(Lead.status == status)
    if city and city.strip():
        query = query.where(func.lower(Lead.city).like(f"%{city.strip().lower()}%"))
    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        query = query.where(
            (func.lower(Lead.company_name).like(search_term)) |
            (func.lower(Lead.email).like(search_term)) |
            (func.lower(Lead.phone).like(search_term)) |
            (func.lower(Lead.city).like(search_term))
        )
    if assigned_user_id and str(assigned_user_id).strip():
        query = query.where(Lead.assigned_user_id == int(assigned_user_id))
    
    query = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    leads = result.scalars().all()

    if request.headers.get("HX-Request"):
        if view == "board":
            return templates.TemplateResponse(
                "lead_board.html", 
                {"request": request, "leads": leads}
            )
        elif view == "compact":
            return templates.TemplateResponse(
                "recent_leads_table.html", 
                {"request": request, "leads": leads}
            )
        return templates.TemplateResponse(
            "lead_table_wrap.html", 
            {"request": request, "leads": leads}
        )
    
    return leads


@router.get("/reminders")
async def upcoming_reminders(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming follow-up reminders."""
    query = select(Lead).where(
        Lead.next_follow_up_date.isnot(None),
        Lead.status.notin_(["Closed Deal", "Rejected"])
    ).order_by(Lead.next_follow_up_date.asc()).limit(5)
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return templates.TemplateResponse(
        "reminders_widget.html", 
        {"request": request, "leads": leads, "now": datetime.now()}
    )


@router.get("/count")
async def lead_count(db: AsyncSession = Depends(get_db)):
    """Get total and today's leads count for dashboard."""
    total_result = await db.execute(select(func.count(Lead.id)))
    total = total_result.scalar_one()
    
    # SQLite friendly query for today's leads
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= today_start)
    )
    today = today_result.scalar_one()

    # Active pipelines
    pipelines_result = await db.execute(
        select(func.count(LeadPipeline.id)).where(LeadPipeline.is_active == True)
    )
    active_pipelines = pipelines_result.scalar_one()

    # Closed deals
    closed_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.status == "Closed Deal")
    )
    closed = closed_result.scalar_one()

    # Stage breakdown
    stages_query = select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    stages_result = await db.execute(stages_query)
    stage_breakdown = {row[0]: row[1] for row in stages_result.all()}

    # Agent breakdown
    agents_query = select(User.full_name, func.count(Lead.id)).join(Lead, User.id == Lead.assigned_user_id).group_by(User.full_name)
    agents_result = await db.execute(agents_query)
    agents_breakdown = {row[0]: row[1] for row in agents_result.all()}

    # High potential leads (Score > 70)
    hp_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.ai_score >= 70)
    )
    high_potential = hp_result.scalar_one()

    # Opportunity tags breakdown (requires some parsing as it's a JSON string)
    # Since we can't easily parse JSON in SQLite query for counts, we'll fetch them and parse in Python for now
    opp_result = await db.execute(select(Lead.opportunity_tags).where(Lead.opportunity_tags.isnot(None)))
    all_tags = []
    for row in opp_result.scalars().all():
        try:
            all_tags.extend(json.loads(row))
        except: pass
    
    from collections import Counter
    opportunity_stats = dict(Counter(all_tags))

    return {
        "total_leads": total,
        "new_leads_today": today,
        "active_pipelines": active_pipelines,
        "closed_deals": closed,
        "stage_breakdown": stage_breakdown,
        "agents_breakdown": agents_breakdown,
        "high_potential": high_potential,
        "opportunity_stats": opportunity_stats
    }


@router.get("/trends")
async def lead_trends(db: AsyncSession = Depends(get_db)):
    """Fetch data for dashboard interactive charts."""
    # 1. Timeline: Leads discovered over last 14 days
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    timeline_labels = []
    timeline_data = []

    for i in range(13, -1, -1):
        target_date = today - timedelta(days=i)
        next_date = target_date + timedelta(days=1)
        
        # SQLite compatible date filtering
        day_count_result = await db.execute(
            select(func.count(Lead.id)).where(Lead.created_at >= target_date, Lead.created_at < next_date)
        )
        count = day_count_result.scalar_one()
        
        # Formatting string as 'Jan 01'
        timeline_labels.append(target_date.strftime("%b %d"))
        timeline_data.append(count)

    # 2. Quality Distribution
    quality_result = await db.execute(select(Lead.ai_score_label, func.count(Lead.id)).group_by(Lead.ai_score_label))
    quality_raw = {row[0]: row[1] for row in quality_result.all()}
    
    # Ensure all labels exist
    quality_stats = {
        "High": quality_raw.get("High", 0),
        "Medium": quality_raw.get("Medium", 0),
        "Low": quality_raw.get("Low", 0),
        "Unscored": quality_raw.get("Unscored", 0) + quality_raw.get(None, 0)
    }

    return {
        "timeline": {
            "labels": timeline_labels,
            "data": timeline_data
        },
        "quality": quality_stats
    }


@router.post("/bulk-status")
async def bulk_update_status(
    data: dict, 
    db: AsyncSession = Depends(get_db)
):
    """Update status for multiple leads at once."""
    lead_ids = data.get("lead_ids", [])
    new_status = data.get("status")
    
    if not lead_ids or not new_status:
        raise HTTPException(status_code=400, detail="Invalid data")

    # Fetch leads
    result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    leads = result.scalars().all()

    for lead in leads:
        if lead.status != new_status:
            # Add activity
            activity = LeadActivity(
                lead_id=lead.id,
                activity_type="Bulk Status Changed",
                description=f"Status changed from '{lead.status}' to '{new_status}'"
            )
            db.add(activity)
            lead.status = new_status
    
    await db.commit()
    return {"detail": f"Updated {len(leads)} leads"}


@router.post("/bulk-assign")
async def bulk_assign_leads(
    data: dict, 
    db: AsyncSession = Depends(get_db)
):
    """Assign multiple leads to a user at once."""
    lead_ids = data.get("lead_ids", [])
    user_id = data.get("assigned_user_id")
    
    if not lead_ids:
        raise HTTPException(status_code=400, detail="Invalid data")

    # Fetch leads
    result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    leads = result.scalars().all()

    for lead in leads:
        lead.assigned_user_id = user_id
        # Add activity
        activity = LeadActivity(
            lead_id=lead.id,
            activity_type="Lead Assigned",
            description=f"Lead assigned to user ID {user_id}" if user_id else "Lead unassigned"
        )
        db.add(activity)

    await db.commit()
    return {"detail": f"Assigned {len(leads)} leads"}


@router.get("/export")
async def export_leads(
    pipeline_id: Optional[Union[int, str]] = Query(None),
    status: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    assigned_user_id: Optional[Union[int, str]] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Export leads to a CSV file."""
    query = select(Lead)
    if pipeline_id and str(pipeline_id).strip():
        query = query.where(Lead.pipeline_id == int(pipeline_id))
    if status and status.strip():
        query = query.where(Lead.status == status)
    if city and city.strip():
        query = query.where(func.lower(Lead.city).like(f"%{city.strip().lower()}%"))
    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        query = query.where(
            (func.lower(Lead.company_name).like(search_term)) |
            (func.lower(Lead.email).like(search_term)) |
            (func.lower(Lead.phone).like(search_term))
        )
    if assigned_user_id and str(assigned_user_id).strip():
        query = query.where(Lead.assigned_user_id == int(assigned_user_id))
    
    result = await db.execute(query.order_by(Lead.created_at.desc()))
    leads = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Company Name", "Phone", "Email", "Website", 
        "City", "AI Score", "AI Label", "Rating", "Status", "Social Links", "Opportunity Tags", "Created At"
    ])
    
    for lead in leads:
        writer.writerow([
            lead.id, lead.company_name, lead.phone, lead.email, lead.website,
            lead.city, lead.ai_score, lead.ai_score_label, lead.rating, lead.status, lead.social_links, lead.opportunity_tags, lead.created_at.strftime("%Y-%m-%d %H:%M")
        ])
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="leads_export_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    }
    
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv",
        headers=headers
    )


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single lead by ID."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/", response_model=LeadOut)
async def create_lead(lead: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Create a new lead manually."""
    db_lead = Lead(**lead.model_dump())
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)
    return db_lead


# --- Lead Activities ---
@router.get("/{lead_id}/activities", response_model=List[LeadActivityOut])
async def list_lead_activities(
    lead_id: int, db: AsyncSession = Depends(get_db)
):
    """Get the activity timeline for a lead."""
    result = await db.execute(
        select(LeadActivity)
        .where(LeadActivity.lead_id == lead_id)
        .order_by(LeadActivity.created_at.desc())
    )
    return result.scalars().all()


@router.put("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int,
    lead_update: LeadUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a lead's details or status."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    db_lead = result.scalar_one_or_none()
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = lead_update.model_dump(exclude_unset=True)

    # Track status changes as activities
    if "status" in update_data and update_data["status"] != db_lead.status:
        activity = LeadActivity(
            lead_id=lead_id,
            activity_type="Status Changed",
            description=f"Status changed from '{db_lead.status}' to '{update_data['status']}'"
        )
        db.add(activity)

    for key, value in update_data.items():
        setattr(db_lead, key, value)

    await db.commit()
    await db.refresh(db_lead)
    return db_lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    db_lead = result.scalar_one_or_none()
    if not db_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(db_lead)
    await db.commit()
    return {"detail": "Lead deleted"}



@router.post("/{lead_id}/activities", response_model=LeadActivityOut)
async def add_lead_activity(
    lead_id: int,
    activity: LeadActivityCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add an activity to a lead's timeline."""
    db_activity = LeadActivity(lead_id=lead_id, **activity.model_dump())
    db.add(db_activity)
    await db.commit()
    await db.refresh(db_activity)
    return db_activity


@router.get("/{lead_id}/email-template")
async def generate_email_template(
    lead_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a smart email template based on lead's opportunity tags."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # Get user settings
    settings_result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = settings_result.scalar_one_or_none()
    
    signature = f"Best,\n{current_user.full_name or 'Your Name'}"
    if settings and settings.email_signature:
        signature = settings.email_signature
        
    tags = []
    import json
    if lead.opportunity_tags:
        try:
            tags = json.loads(lead.opportunity_tags)
        except:
            pass
            
    name = lead.company_name
    
    # Simple smart templates based on AI detected gaps
    if "No Website" in tags:
        subject = f"Quick question about {name}"
        body = f"Hi there,\n\nI was looking for {name} online but noticed you don't seem to have a website. We help businesses in your industry build high-converting websites to drive more local traffic.\n\nWould you be open to a quick 5-minute chat to see how we could help?\n\n{signature}"
    elif "Needs Reviews" in tags:
        subject = f"Ideas for {name}'s online reputation"
        body = f"Hi there,\n\nI noticed {name} has some room to grow your overall Google rating. We specialize in helping businesses like yours automatically collect 5-star reviews from happy customers.\n\nCould we jump on a brief call this week to discuss a strategy?\n\n{signature}"
    elif "No Socials" in tags:
        subject = f"Increasing {name}'s online presence"
        body = f"Hi there,\n\nI noticed {name} doesn't seem to have much of a presence on social media. It's a huge missed opportunity to connect with local customers.\n\nOur team helps businesses like yours manage social channels effortlessly. Would you be open to seeing a quick proposal?\n\n{signature}"
    else:
        subject = f"Partnership opportunity with {name}"
        body = f"Hi there,\n\nI came across {name} and was really impressed by your business. Our company provides tools to help you scale even further.\n\nWould you have 5 minutes next Tuesday for a quick intro call?\n\n{signature}"
        
    return {"subject": subject, "body": body}

