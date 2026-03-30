from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "leadgen_crm",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.services.scraper_tasks", "app.services.outreach_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Celery Beat schedule
celery_app.conf.beat_schedule = {
    "run-all-pipelines-daily": {
        "task": "run_all_pipelines",
        "schedule": crontab(hour=3, minute=0),
    },
    "process-outreach-sequences-hourly": {
        "task": "process_outreach_sequences",
        "schedule": crontab(minute=0), # Every hour
    },
}
