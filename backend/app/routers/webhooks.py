from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import aiohttp
import os
import json

from app.core.database import get_db
from app.models.models import Lead, LeadPipeline, LeadActivity, User

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "leadgen_meta_crm_secret")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")

# 1. Verification Endpoint for Meta (Required by Facebook App Dashboard)
@router.get("/meta")
async def verify_meta_webhook(
    request: Request,
):
    """
    Meta Developer Portal hits this endpoint via GET to verify your webhook URL.
    You must provide the exact same verify token in your app portal.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            return int(challenge)
        raise HTTPException(status_code=403, detail="Verification token mismatch")
    
    raise HTTPException(status_code=400, detail="Missing parameters")

# Background Task to fetch the actual lead data from Graph API securely
async def fetch_and_save_meta_lead(lead_id: str, form_id: str, db: AsyncSession):
    if not META_ACCESS_TOKEN:
        print(f"ERROR: Cannot fetch Meta Lead {lead_id} without META_ACCESS_TOKEN in .env")
        return

    async with aiohttp.ClientSession() as session:
        url = f"https://graph.facebook.com/v18.0/{lead_id}?access_token={META_ACCESS_TOKEN}"
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Failed to fetch lead {lead_id} from Meta APIs")
                return
            
            lead_data = await response.json()
            
            # Parse custom form fields
            parsed_data = {
                "email": "",
                "phone": "",
                "company_name": "Meta Lead Form Submission",
                "full_name": ""
            }
            
            field_data = lead_data.get("field_data", [])
            for field in field_data:
                name = field.get("name")
                value = field.get("values", [""])[0]
                
                if name == "email": parsed_data["email"] = value
                if name in ["phone_number", "phone"]: parsed_data["phone"] = value
                if name == "company_name": parsed_data["company_name"] = value
                if name == "full_name": parsed_data["full_name"] = value

            if not parsed_data["company_name"] or parsed_data["company_name"] == "Meta Lead Form Submission":
                parsed_data["company_name"] = parsed_data["full_name"] or "Meta Inbound Lead"

            # 1. Find or create a dedicated "Meta Campaigns" Pipeline
            pipeline_result = await db.execute(select(LeadPipeline).where(LeadPipeline.name == "Inbound Meta Campaigns"))
            pipeline = pipeline_result.scalar_one_or_none()
            
            if not pipeline:
                # Assign to user 1 by default (the admin)
                first_user = await db.execute(select(User).limit(1))
                admin = first_user.scalar_one()
                
                pipeline = LeadPipeline(
                    user_id=admin.id,
                    name="Inbound Meta Campaigns",
                    industry="Social Media Ads",
                    location="Global",
                    platform="Meta Ads",
                    is_active=True
                )
                db.add(pipeline)
                await db.commit()
                await db.refresh(pipeline)
            
            # 2. Prevent exact duplicates
            from sqlalchemy.orm import selectinload
            existing_lead = await db.execute(
                select(Lead).where(
                    Lead.email == parsed_data["email"], 
                    Lead.pipeline_id == pipeline.id
                )
            )
            if existing_lead.scalar_one_or_none():
                print(f"Lead {parsed_data['email']} already exists in CRM.")
                return

            # 3. Create the Lead
            new_lead = Lead(
                pipeline_id=pipeline.id,
                company_name=parsed_data["company_name"],
                email=parsed_data["email"],
                phone=parsed_data["phone"],
                source="Meta Lead Ads",
                status="New Lead",
                ai_score=85, # Meta leads are high intent
                ai_score_label="High",
                opportunity_tags=json.dumps(["Inbound Ads", f"Form {form_id}"])
            )
            db.add(new_lead)
            
            # Increase total counter on pipeline
            pipeline.total_leads_found = (pipeline.total_leads_found or 0) + 1
            
            await db.commit()
            await db.refresh(new_lead)
            
            # 4. Log the activity securely
            activity = LeadActivity(
                lead_id=new_lead.id,
                activity_type="Lead Created",
                description="Lead originated from a Facebook/Instagram Ad Campaign"
            )
            db.add(activity)
            await db.commit()

# 2. Main Webhook Receiver
@router.post("/meta")
async def receive_meta_lead(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives incoming payload from Meta whenever someone submits an Instant Form on FB/IG.
    """
    payload = await request.json()
    
    # Meta sends an array of "entries" containing standard messaging updates
    if payload.get("object") == "page":
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                # Standard Leadgen payload
                if change.get("value") and "leadgen_id" in change["value"]:
                    lead_id = change["value"]["leadgen_id"]
                    form_id = change["value"].get("form_id")
                    
                    # Offload the Graph API GET request to the background
                    background_tasks.add_task(fetch_and_save_meta_lead, lead_id, form_id, db)
                    
        return {"status": "ok"}
        
    raise HTTPException(status_code=400, detail="Invalid payload")


# 3. Zapier / Make.com Direct Webhook (Easier Alternative)
@router.post("/zapier")
async def zapier_generic_webhook(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    If you don't want to setup a Meta App, you can catch the Meta Lead with Zapier
    and POST to this endpoint with JSON.
    Expected: {"company_name": "X", "email": "Y", "phone": "Z", "campaign": "Meta"}
    """
    pipeline_result = await db.execute(select(LeadPipeline).where(LeadPipeline.name == "Inbound Meta Campaigns"))
    pipeline = pipeline_result.scalar_one_or_none()
    
    if not pipeline:
        first_user = await db.execute(select(User).limit(1))
        admin = first_user.scalar_one()
        pipeline = LeadPipeline(
            user_id=admin.id, name="Inbound Meta Campaigns", industry="Social Media Ads",
            location="Global", platform="Meta Ads", is_active=True
        )
        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)

    new_lead = Lead(
        pipeline_id=pipeline.id,
        company_name=data.get("company_name", data.get("full_name", "Inbound Zapier Lead")),
        email=data.get("email"),
        phone=data.get("phone"),
        source="Zapier Webhook",
        status="New Lead",
        ai_score=85,
        ai_score_label="High",
        opportunity_tags=json.dumps(["Inbound Data", data.get("campaign", "Campaign Tracker")])
    )
    db.add(new_lead)
    pipeline.total_leads_found = (pipeline.total_leads_found or 0) + 1
    
    await db.commit()
    await db.refresh(new_lead)
    
    activity = LeadActivity(lead_id=new_lead.id, activity_type="Lead Created", description="Lead received from Zapier webhook")
    db.add(activity)
    await db.commit()
    return {"status": "success", "lead_id": new_lead.id}
