# LeadGen CRM — Product Specification

## Overview

LeadGen CRM is a SaaS platform that automatically discovers new business leads and manages them inside a built-in CRM system.

Instead of manually searching for leads every day, users define their target criteria once, and the system continuously scrapes public sources to discover new potential clients daily.

The platform then automatically inserts these leads into a CRM workflow, allowing businesses to manage outreach, track conversations, assign team members, and close deals.

This system combines Lead Generation + CRM + Automation into one platform.

Primary competitors include tools like Apollo, HubSpot, and Pipedrive, but this platform focuses heavily on automated lead discovery. you can inspire from them for the features but the main focus is automated lead discovery.

---

# Core Concept

LeadGen CRM workflow:

User defines lead criteria once → system continuously discovers new leads → leads automatically enter CRM pipeline.

The system works like a lead stream, constantly feeding new opportunities into the CRM.

---

# Core Modules

## 1. Lead Pipelines

Users define lead discovery rules once.

Example pipeline configuration:

Industry: Digital Marketing Agencies  
Location: Pune  
Minimum Rating: 3  
Website Required: Yes  

The platform runs automated scraping jobs daily and collects new businesses matching these criteria.

Each pipeline acts as a continuous lead discovery engine.

Users can create multiple pipelines.

Example:

Pipeline 1: Coaching Classes in Nashik  
Pipeline 2: Restaurants in Mumbai  
Pipeline 3: Marketing Agencies in Bangalore

---

## 2. Automated Lead Discovery

The system runs scheduled scraping jobs that collect new businesses.

Sources may include:

Google Maps  
Business directories  
Public company websites  
Startup listings

The system extracts information such as:

Company Name  
Phone Number  
Email Address (if available)  
Website  
Address  
City  
Google Rating  
Social Links  

Before saving, the system performs deduplication checks to avoid storing the same lead multiple times.

Duplicate checks should use:

Phone Number  
Email  
Website  
Company Name similarity

---

## 3. CRM Lead Management

Every discovered lead automatically enters the CRM.

Each lead contains structured information and can move through a sales pipeline.

Default stages:

New Lead  
Contacted  
Interested  
Follow-up  
Closed Deal  
Rejected

Users should be able to change lead stages easily via dropdown or drag-and-drop pipeline UI.

Each lead record should contain:

Basic contact information  
Status  
Assigned employee  
Notes  
Activity history  
Last contact timestamp

---

## 4. Activity Timeline

Every lead maintains a timeline of events.

Example:

March 6 — Lead discovered  
March 7 — Sales rep called client  
March 9 — Client requested proposal  

The activity timeline helps teams track communication history.

---

## 5. Lead Assignment

Leads can be assigned to team members.

Fields:

Assigned User  
Last Interaction  
Next Follow-up Date  

This enables team-based lead management.

---

## 6. Notes System

Users can attach notes to each lead.

Example:

Client interested in website redesign  
Estimated budget ₹40k  
Follow up next week

Notes should appear inside the lead detail panel.

---

## 7. Follow-Up Reminder System

The CRM should allow users to schedule reminders.

Example reminder:

Follow up with ABC Marketing tomorrow at 11 AM.

Reminders appear in:

Dashboard  
Notifications panel

---

## 8. Smart Filters

Users should be able to filter leads using:

Location  
Industry  
Website availability  
Rating  
Pipeline source  
Assigned employee  
Lead stage

Filters should update the table instantly.

---

## 9. Daily Lead Feed

The dashboard should show how many new leads were discovered.

Example widget:

23 New Leads Found Today

Users should be able to click this widget to view newly discovered leads.

---

# Automation System

Lead pipelines must run automatically.

Use scheduled background workers.

Example schedule:

Daily at 03:00 AM.

Each pipeline should store:

Last Run Timestamp  
Total Leads Found  
Total New Leads

---

# Suggested Backend Architecture

Backend Framework:

Python (FastAPI or Flask)

Scraping Tools:

Playwright  
BeautifulSoup  
Requests  

Task Queue:

Celery + Redis

Database:

PostgreSQL

Frontend:

React Dashboard or server-rendered templates.

Hosting options:

Render  
DigitalOcean  
AWS

---

# Data Models (Conceptual)

LeadPipeline

id  
user_id  
industry  
location  
filters  
created_at  
last_run  

Lead

id  
pipeline_id  
company_name  
phone  
email  
website  
address  
city  
rating  
status  
assigned_user  
created_at  

LeadActivity

id  
lead_id  
activity_type  
description  
created_at  

LeadNotes

id  
lead_id  
note  
created_at  

---

# UI/UX Design Guidelines

The interface should follow a minimalist design philosophy.

Avoid clutter and excessive visual elements.

Use clean spacing and simple components.

The platform should feel similar to modern SaaS dashboards with a calm and professional interface.

---

# Color Palette

Primary Theme:

Beige and Brown tones.

Suggested palette:

Background:  
#F5F0E6

Primary Accent:  
#8B6B4F

Secondary Accent:  
#B89B7A

Card Background:  
#FFFFFF

Text Primary:  
#3E2F24

Borders:  
#E5DED3

This palette should create a warm, neutral, professional interface.

---

# Layout Structure

Left Sidebar Navigation

Dashboard  
Leads  
Pipelines  
Team  
Activity  
Settings

Main Content Area

Tables for lead lists  
Cards for metrics  
Drawer or modal for lead details

Tables should remain simple and readable.

Avoid heavy visual components.

---

# Design Principles

Minimalist  
Clean whitespace  
Neutral color tones  
Readable typography  
Fast interactions  

No excessive animations.

The interface should feel calm and professional.

---

# Future Features

AI Lead Scoring

Automatically score leads as:

High Potential  
Medium Potential  
Low Potential

Based on:

Reviews  
Website quality  
Business presence

---

Email Outreach

Allow sending outreach emails directly from the CRM.

---

Opportunity Detection

Detect businesses with:

No website  
Low ratings  
New openings

These leads can be flagged as high opportunity prospects.

---

# Product Vision

LeadGen CRM aims to become an automated sales intelligence platform where businesses no longer need to manually search for leads.

The system continuously discovers new potential customers and feeds them into a structured CRM pipeline where teams can manage outreach and close deals efficiently.

The ultimate goal is to turn lead discovery into a continuous automated process.