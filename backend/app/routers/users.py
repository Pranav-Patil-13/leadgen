from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.models.models import User, UserSettings
from app.core.security import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/users", tags=["users"])

class UserSchema(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

from typing import Optional

class UserSettingsUpdate(BaseModel):
    sender_name: Optional[str] = None
    reply_to_email: Optional[str] = None
    email_signature: Optional[str] = None

@router.get("/settings")
async def get_user_settings(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the current user's settings."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Return defaults if none
        return {
            "sender_name": current_user.full_name or "",
            "reply_to_email": current_user.email,
            "email_signature": f"Best,\n{current_user.full_name or 'Your Name'}"
        }
    
    return {
        "sender_name": settings.sender_name,
        "reply_to_email": settings.reply_to_email,
        "email_signature": settings.email_signature
    }

@router.post("/settings")
async def update_user_settings(
    settings_data: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update or create user settings."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    if settings_data.sender_name is not None:
        settings.sender_name = settings_data.sender_name
    if settings_data.reply_to_email is not None:
        settings.reply_to_email = settings_data.reply_to_email
    if settings_data.email_signature is not None:
        settings.email_signature = settings_data.email_signature
        
    await db.commit()
    return {"status": "success"}

@router.get("/", response_model=List[UserSchema])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()

from app.core.security import get_password_hash
from app.schemas.schemas import UserCreate

@router.post("/")
async def invite_user(
    user_data: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Invite/Create a new team member."""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"status": "success", "user_id": new_user.id}

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user
