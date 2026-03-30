from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for local dev, PostgreSQL for production
# To use PostgreSQL, set DATABASE_URL in .env:
#   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/leadgen_crm
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./leadgen.db")

# Engine configuration (SSL is required for production cloud databases like Supabase)
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={"ssl": True} if DATABASE_URL.startswith("postgresql") else {}
)
async_session_factory = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with async_session_factory() as session:
        yield session
