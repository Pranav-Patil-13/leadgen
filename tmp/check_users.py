import asyncio
import os
import sys

# Inject backend into sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "backend"))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, "backend", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./leadgen.db")

async def check():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL, connect_args={"ssl": True} if DATABASE_URL.startswith("postgresql") else {})
    
    async with engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT email FROM users"))
            print("Users in DB:", [r[0] for r in res])
        except Exception as e:
            print(f"Error reading users: {e}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
