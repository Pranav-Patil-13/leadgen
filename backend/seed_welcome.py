import asyncio
from app.core.database import async_session_factory
from app.models.models import EmailCampaign, CampaignStep, User
from sqlalchemy import select

async def seed_welcome_sequence():
    async with async_session_factory() as session:
        # Get the first user
        res = await session.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        
        if not user:
            print("No user found. Please register first!")
            return

        # Check if already exists
        exists = await session.execute(select(EmailCampaign).where(EmailCampaign.name == "Welcome Sequence", EmailCampaign.user_id == user.id))
        if exists.scalars().first():
            print("Welcome Sequence already exists.")
            return

        campaign = EmailCampaign(
            user_id=user.id,
            name="Welcome Sequence"
        )
        session.add(campaign)
        await session.flush()

        step1 = CampaignStep(
            campaign_id=campaign.id,
            step_number=1,
            subject="Welcome to our network, {company_name}!",
            body="Hi {company_name},\n\nWe're excited to connect with you. We've been following your progress in the industry and would love to chat more about how we can collaborate.\n\nBest,\nThe LeadGen Team",
            delay_days=0
        )
        
        step2 = CampaignStep(
            campaign_id=campaign.id,
            step_number=2,
            subject="Quick thoughts on your strategy",
            body="Hi {company_name},\n\nJust following up on my previous email. I was taking a look at your website today and had a specific idea that might help you guys out.\n\nDo you have 10 minutes later this week?\n\nBest,\nThe LeadGen Team",
            delay_days=3
        )

        session.add(step1)
        session.add(step2)
        await session.commit()
        print(f"Successfully created Welcome Sequence for user {user.email}")

if __name__ == "__main__":
    asyncio.run(seed_welcome_sequence())
