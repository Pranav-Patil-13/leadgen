from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    pipelines = relationship("LeadPipeline", back_populates="owner")
    assigned_leads = relationship("Lead", back_populates="assigned_to")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    # campaigns...

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Email Outreach Settings
    sender_name = Column(String, nullable=True)
    reply_to_email = Column(String, nullable=True)
    email_signature = Column(Text, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="settings")

class LeadPipeline(Base):
    __tablename__ = "lead_pipelines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g., "Marketing Agencies in Pune"
    industry = Column(String, nullable=False)
    location = Column(String, nullable=False)
    platform = Column(String, default="Google Maps") # Google Maps, Reddit, Twitter, etc.
    minimum_rating = Column(String, default="0")
    requires_website = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_run = Column(DateTime, nullable=True)

    # Metrics
    total_leads_found = Column(Integer, default=0)

    # Relationships
    owner = relationship("User", back_populates="pipelines")
    leads = relationship("Lead", back_populates="pipeline")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("lead_pipelines.id"), nullable=False)
    
    company_name = Column(String, nullable=False, index=True)
    phone = Column(String, index=True)
    email = Column(String, index=True)
    website = Column(String)
    address = Column(String)
    city = Column(String)
    rating = Column(String)
    google_maps_url = Column(String)
    social_links = Column(String) # JSON string or comma separated
    source = Column(String, default="Scraper") # Scraper, Reddit, Manual, etc.
    intent_data = Column(Text, nullable=True) # To store post content or snippet for intent analysis
    
    # CRM Status: New Lead, Contacted, Interested, Follow-up, Closed Deal, Rejected
    status = Column(String, default="New Lead", index=True)
    
    # AI Scoring & Intelligence
    ai_score = Column(Integer, default=0) # 0-100
    ai_score_label = Column(String, default="Low") # Low, Medium, High
    opportunity_tags = Column(String, nullable=True) # JSON array of strings e.g., ["No Website", "Low Rating"]
    
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_contacted_at = Column(DateTime, nullable=True)
    next_follow_up_date = Column(DateTime, nullable=True)

    # Relationships
    pipeline = relationship("LeadPipeline", back_populates="leads")
    assigned_to = relationship("User", back_populates="assigned_leads")
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    campaigns = relationship("CampaignLead", back_populates="lead")
    tasks = relationship("Task", back_populates="lead", cascade="all, delete-orphan")

class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    activity_type = Column(String, nullable=False) # e.g., "Note Added", "Status Changed", "Email Sent"
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="activities")

class LeadNote(Base):
    __tablename__ = "lead_notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    note_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="notes")

class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    steps = relationship("CampaignStep", back_populates="campaign", cascade="all, delete-orphan")
    leads = relationship("CampaignLead", back_populates="campaign", cascade="all, delete-orphan")

class CampaignStep(Base):
    __tablename__ = "campaign_steps"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("email_campaigns.id"), nullable=False)
    step_number = Column(Integer, nullable=False) # 1, 2, 3...
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    delay_days = Column(Integer, default=0) # Delay after previous step or after start (for step 1)
    
    # Relationships
    campaign = relationship("EmailCampaign", back_populates="steps")

class CampaignLead(Base):
    __tablename__ = "campaign_leads"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("email_campaigns.id"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    
    current_step = Column(Integer, default=1)
    status = Column(String, default="Active") # Active, Completed, Paused, Unsubscribed
    last_step_completed_at = Column(DateTime, nullable=True)
    next_step_due_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("EmailCampaign", back_populates="leads")
    lead = relationship("Lead", back_populates="campaigns")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True) # Optional association with a lead
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    lead = relationship("Lead", back_populates="tasks")
