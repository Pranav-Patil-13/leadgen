import os
import sys

# Calculate and inject the backend folder into sys.path for cross-module accessibility
current_dir = os.path.dirname(os.path.abspath(__file__))
# BASE_DIR is the 'backend' folder
BASE_DIR = os.path.dirname(current_dir)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from datetime import datetime, date

from app.core.database import engine, Base
from app.core.security import get_current_user
from app.models.models import User
from app.routers import leads, pipelines, notes, auth, users, campaigns, tasks
from fastapi.responses import RedirectResponse
from fastapi import Depends


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (for dev; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


# Initialize FastAPI App
app = FastAPI(
    title="LeadGen CRM",
    description="Automated lead discovery and CRM system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Register API routers
app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(pipelines.router)
app.include_router(notes.router)
app.include_router(users.router)
app.include_router(campaigns.router)
app.include_router(tasks.router)


# --- HTMX Page Routes ---

async def get_authenticated_user(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return None
    return user

@app.get("/")
async def dashboard(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user,
        "today": date.today().isoformat()
    })

@app.get("/leads")
async def leads_page(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("leads.html", {"request": request, "user": user})

@app.get("/pipelines")
async def pipelines_page(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("pipelines.html", {"request": request, "user": user})

@app.get("/team")
async def team_page(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("team.html", {"request": request, "user": user})

@app.get("/outreach")
async def outreach_page(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("campaigns.html", {"request": request, "user": user})

@app.get("/calendar")
async def calendar_page(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("calendar.html", {"request": request, "user": user})

@app.get("/activity")
async def activity_page(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("activity.html", {"request": request, "user": user})

@app.get("/settings")
async def settings_page(request: Request, user: User = Depends(get_authenticated_user)):
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
