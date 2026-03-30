import asyncio
import os
import sys

# Inject backend into sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(current_dir)
backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.append(backend_path)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from app.core.security import get_password_hash
from app.models.models import Base

load_dotenv(os.path.join(backend_path, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./leadgen.db")

# Force SSL for cloud connections
if DATABASE_URL.startswith("postgresql") and "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL += f"{sep}sslmode=require"

async def reset_database():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_async_engine(
        DATABASE_URL, 
        connect_args={"ssl": True} if DATABASE_URL.startswith("postgresql") else {}
    )
    
    async with engine.begin() as conn:
        print("Ensuring tables are created...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables ready.")

        print("Wiping existing data...")
        tables = [
            "tasks", "campaign_leads", "campaign_steps", "email_campaigns", 
            "lead_activities", "lead_notes", "leads", "lead_pipelines", 
            "user_settings", "users"
        ]
        
        for table in tables:
            try:
                if DATABASE_URL.startswith("postgresql"):
                    await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                else:
                    await conn.execute(text(f"DELETE FROM {table};"))
                    # Only reset sequence for sqlite
                    try:
                        await conn.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}';"))
                    except:
                        pass
                print(f"  - Cleared {table}")
            except Exception as e:
                print(f"  - Skip {table} (no data or error)")

        print("\nCreating fresh Admin User...")
        admin_email = "admin@leadgen.com"
        admin_pass = "admin123"
        hashed_pass = get_password_hash(admin_pass)
        
        await conn.execute(
            text("INSERT INTO users (email, hashed_password, full_name, is_active) VALUES (:email, :pass, :name, :active)"),
            {"email": admin_email, "pass": hashed_pass, "name": "System Admin", "active": True}
        )
        print(f"  + User created: {admin_email} / {admin_pass}")

        print("\nConfiguring Optimized Software Solution Pipelines...")
        
        # We need the user_id of the admin we just created.
        # In SQLite/Postgres with RESTART IDENTITY, it should be 1.
        user_id = 1
        
        pipelines = [
            ("Manufacturing & Supply Chain", "Process Automation, ERP", "Industrial Zones", user_id),
            ("E-commerce & D2C", "Custom Storefronts, Shopify Apps", "Global", user_id),
            ("Financial Services", "Fintech, Portfolio Trackers", "Metros", user_id)
        ]

        for name, industry, location, uid in pipelines:
            await conn.execute(
                text("INSERT INTO lead_pipelines (user_id, name, industry, location, platform) VALUES (:uid, :name, :ind, :loc, :plat)"),
                {"uid": uid, "name": name, "ind": industry, "loc": location, "plat": "Google Maps"}
            )
            print(f"  + Pipeline Seat: {name}")

    print("\nSUCCESS: CRM is now fresh and ready for targeting.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())
