import asyncio
from app.services.scraper_tasks import process_pipeline
from app.core.database import engine

async def main():
    try:
        print("Running pipeline 1...")
        res = await process_pipeline(1)
        print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
