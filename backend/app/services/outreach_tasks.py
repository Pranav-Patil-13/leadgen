import asyncio
from typing import List
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime, timedelta
import json

from app.core.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.models import EmailCampaign, CampaignStep, CampaignLead, Lead, LeadActivity

@celery_app.task(name="process_outreach_sequences")
def process_outreach_sequences_task():
    """Celery task to process all active campaign steps across all leads."""
    return asyncio.run(process_automation())

async def process_automation():
    """Logic to find and process leads due for their next automation step."""
    async with async_session_factory() as session:
        now = datetime.utcnow()
        
        # 1. Find all active campaign leads where next_step_due_at <= now
        stmt = (
            select(CampaignLead)
            .where(CampaignLead.status == "Active")
            .where(CampaignLead.next_step_due_at <= now)
        )
        result = await session.execute(stmt)
        campaign_leads = result.scalars().all()
        
        processed_count = 0
        for cl in campaign_leads:
            # 2. Get the specific step details
            step_stmt = (
                select(CampaignStep)
                .where(CampaignStep.campaign_id == cl.campaign_id)
                .where(CampaignStep.step_number == cl.current_step)
            )
            step_res = await session.execute(step_stmt)
            step = step_res.scalars().first()
            
            if not step:
                # No more steps or error - mark as completed
                cl.status = "Completed"
                continue

            # 3. Fetch lead details for merge tags
            lead = await session.get(Lead, cl.lead_id)
            if not lead or not lead.email:
                cl.status = "Error (No Email)"
                continue

            # 4. Perform "Send" (Mocking for now)
            # Define tags mapping
            tags = {
                "{company}": lead.company_name or "there",
                "{company_name}": lead.company_name or "there", # Backward compatibility
                "{city}": lead.city or "your area",
                "{website}": lead.website or "your site",
                "{phone}": lead.phone or "your phone",
                "{email}": lead.email or "your email",
                "{address}": lead.address or "your location",
            }

            # Replace tags in subject/body
            subject = step.subject
            body = step.body
            for tag, value in tags.items():
                subject = subject.replace(tag, value)
                body = body.replace(tag, value)

            # Mark in activity log
            activity = LeadActivity(
                lead_id=lead.id,
                activity_type="Email Sent",
                description=f"Automated Sequence '{step.subject}' sent to {lead.email}"
            )
            session.add(activity)
            lead.status = "Contacted"
            lead.last_contacted_at = now

            # 5. Schedule next step
            next_step_num = cl.current_step + 1
            next_step_stmt = (
                select(CampaignStep)
                .where(CampaignStep.campaign_id == cl.campaign_id)
                .where(CampaignStep.step_number == next_step_num)
            )
            next_step_res = await session.execute(next_step_stmt)
            next_step = next_step_res.scalars().first()

            if next_step:
                cl.current_step = next_step_num
                cl.last_step_completed_at = now
                cl.next_step_due_at = now + timedelta(days=next_step.delay_days)
            else:
                cl.status = "Completed"
                cl.last_step_completed_at = now
                cl.next_step_due_at = None

            processed_count += 1
        
        await session.commit()
        return processed_count
