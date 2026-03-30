from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.models import EmailCampaign, CampaignStep, CampaignLead, Lead, User
from app.core.security import get_current_user
from app.schemas.schemas import EmailCampaignCreate, EmailCampaignOut, CampaignLeadAdd
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])
templates = Jinja2Templates(directory="templates")

@router.post("/", response_model=EmailCampaignOut)
async def create_campaign(
    campaign: EmailCampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new email outreach campaign with steps."""
    new_campaign = EmailCampaign(
        user_id=current_user.id,
        name=campaign.name
    )
    db.add(new_campaign)
    await db.flush()

    for step_data in campaign.steps:
        step = CampaignStep(
            campaign_id=new_campaign.id,
            **step_data.dict()
        )
        db.add(step)
    
    await db.commit()
    await db.refresh(new_campaign)
    
    # Reload with steps
    stmt = select(EmailCampaign).where(EmailCampaign.id == new_campaign.id).options(selectinload(EmailCampaign.steps))
    res = await db.execute(stmt)
    return res.scalar_one()

@router.get("/", response_model=List[EmailCampaignOut])
async def list_campaigns(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all campaigns for the current user."""
    stmt = select(EmailCampaign).where(EmailCampaign.user_id == current_user.id).options(selectinload(EmailCampaign.steps))
    result = await db.execute(stmt)
    campaigns = result.scalars().all()
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "campaign_list_partial.html", 
            {"request": request, "campaigns": campaigns}
        )
    
    return campaigns

@router.post("/add-leads")
async def add_leads_to_campaign(
    data: CampaignLeadAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add multiple leads to an automated sequence."""
    # Verify campaign ownership
    stmt = select(EmailCampaign).where(EmailCampaign.id == data.campaign_id, EmailCampaign.user_id == current_user.id)
    res = await db.execute(stmt)
    campaign = res.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    added_count = 0
    for lead_id in data.lead_ids:
        # Check if lead already in campaign
        exists_stmt = select(CampaignLead).where(
            CampaignLead.campaign_id == data.campaign_id, 
            CampaignLead.lead_id == lead_id
        )
        exists_res = await db.execute(exists_stmt)
        if exists_res.scalars().first():
            continue

        camp_lead = CampaignLead(
            campaign_id=data.campaign_id,
            lead_id=lead_id,
            next_step_due_at=datetime.utcnow() # Start now
        )
        db.add(camp_lead)
        added_count += 1
    
    await db.commit()
    return {"detail": f"Added {added_count} leads to campaign '{campaign.name}'"}

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete a campaign and its steps."""
    stmt = select(EmailCampaign).where(EmailCampaign.id == campaign_id, EmailCampaign.user_id == current_user.id)
    res = await db.execute(stmt)
    campaign = res.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await db.delete(campaign)
    await db.commit()
    return {"detail": "Campaign deleted"}
