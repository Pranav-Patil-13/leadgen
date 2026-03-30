from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# --- User Schemas ---
class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- LeadPipeline Schemas ---
class LeadPipelineBase(BaseModel):
    name: str
    industry: str
    location: str
    platform: Optional[str] = "Google Maps"
    minimum_rating: Optional[str] = "0"
    requires_website: Optional[bool] = False

class LeadPipelineCreate(LeadPipelineBase):
    pass

class LeadPipelineUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    platform: Optional[str] = None
    minimum_rating: Optional[str] = None
    requires_website: Optional[bool] = None
    is_active: Optional[bool] = None

class LeadPipelineOut(LeadPipelineBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    last_run: Optional[datetime] = None
    total_leads_found: Optional[int] = 0

    class Config:
        from_attributes = True


# --- Lead Schemas ---
class LeadBase(BaseModel):
    company_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    rating: Optional[str] = None
    google_maps_url: Optional[str] = None
    social_links: Optional[str] = None
    ai_score: Optional[int] = 0
    ai_score_label: Optional[str] = "Low"
    opportunity_tags: Optional[str] = None
    source: Optional[str] = "Scraper"
    intent_data: Optional[str] = None

class LeadCreate(LeadBase):
    pipeline_id: int

class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    status: Optional[str] = None
    assigned_user_id: Optional[int] = None
    next_follow_up_date: Optional[datetime] = None
    ai_score: Optional[int] = None
    ai_score_label: Optional[str] = None
    opportunity_tags: Optional[str] = None

class LeadOut(LeadBase):
    id: int
    pipeline_id: int
    status: str
    assigned_user_id: Optional[int] = None
    created_at: datetime
    last_contacted_at: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- LeadActivity Schemas ---
class LeadActivityCreate(BaseModel):
    activity_type: str
    description: str

class LeadActivityOut(LeadActivityCreate):
    id: int
    lead_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- LeadNote Schemas ---
class LeadNoteCreate(BaseModel):
    note_text: str

class LeadNoteOut(LeadNoteCreate):
    id: int
    lead_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Email Campaign Schemas ---
from typing import List, Optional

class CampaignStepBase(BaseModel):
    step_number: int
    subject: str
    body: str
    delay_days: int = 0

class CampaignStepCreate(CampaignStepBase):
    pass

class CampaignStepOut(CampaignStepBase):
    id: int
    campaign_id: int

    class Config:
        from_attributes = True

class EmailCampaignBase(BaseModel):
    name: str
    is_active: bool = True

class EmailCampaignCreate(EmailCampaignBase):
    steps: List[CampaignStepCreate]

class EmailCampaignUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class EmailCampaignOut(EmailCampaignBase):
    id: int
    user_id: int
    created_at: datetime
    steps: List[CampaignStepOut] = []

    class Config:
        from_attributes = True

class CampaignLeadAdd(BaseModel):
    lead_ids: List[int]
    campaign_id: int

# --- Task / Calendar Schemas ---
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: datetime
    is_completed: bool = False
    lead_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    is_completed: Optional[bool] = None

class TaskOut(TaskBase):
    id: int
    user_id: int
    created_at: datetime
    lead_company: Optional[str] = None # For UI convenience

    class Config:
        from_attributes = True
